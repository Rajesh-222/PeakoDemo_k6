# PerfStudio JMX parameter patcher
# Usage: python3 patch_jmx.py <script> <users> <rampup> <loops> <duration>
import re, sys

script, users, rampup, loops, duration = sys.argv[1:6]
use_duration = duration != "-1" and int(duration) > 0

with open(script, "r", encoding="utf-8") as f:
    content = f.read()

def sp(xml, name, val):
    pat = r'(<(?:string|int|long|bool)Prop\s+name="' + re.escape(name) + r'">)[^<]*'
    new, n = re.subn(pat, r'\g<1>' + str(val), xml)
    print(("  SET " if n else "  WARN ") + name + "=" + str(val))
    return new

# Fix absolute local Windows paths -> CI /workspace/ paths
# Handles two-level structure: git-workspaces/<project>/<user>/
path_pattern = r"[A-Za-z]:[/\\][^'\"<>]*?git-workspaces[/\\][^/\\]+[/\\][^/\\]+[/\\]"
fixed_content, path_fixes = re.subn(path_pattern, "/workspace/", content)
if path_fixes:
    fixed_content = fixed_content.replace("\\", "/")
    content = fixed_content
    print("  FIXED " + str(path_fixes) + " absolute path(s) -> /workspace/")
else:
    path_pattern_old = r"[A-Za-z]:[/\\][^'\"<>]*?git-workspaces[/\\][^/\\]+[/\\]"
    fixed_content, path_fixes = re.subn(path_pattern_old, "/workspace/", content)
    if path_fixes:
        fixed_content = fixed_content.replace("\\", "/")
        content = fixed_content
        print("  FIXED " + str(path_fixes) + " absolute path(s) (old structure) -> /workspace/")
    else:
        print("  No absolute paths to fix")

def patch_ultimate_thread_group(xml, vusers, duration):
    # Mirrors buildUltimateThreadGroupXml() in testSuites.js EXACTLY (same 5-step
    # staircase formula) -- a stress test's schedule is baked as literal row numbers at
    # script-generation time, not as ${__P(...)} properties like the flat ThreadGroup,
    # so overriding VUsers/Duration at CI-trigger time means recomputing every row here
    # rather than a simple property-value substitution. No rampup parameter: the step
    # transition is derived purely from vusers/duration, never a user-supplied ramp-up --
    # see buildUltimateThreadGroupXml's matching comment for why (Ramp-up is blocked/hidden
    # in the UI for stress tests entirely).
    steps = 5
    shutdown_s = 30
    step_budget = duration / steps
    step_ramp = max(5, round(step_budget * 0.2))
    t_end = steps * step_budget

    rows = []
    cumulative = 0
    for i in range(1, steps + 1):
        target = vusers if i == steps else round(vusers * i / steps)
        delay = round((i - 1) * step_budget)
        hold = max(0, round(t_end - delay - step_ramp))
        rows.append((target - cumulative, delay, round(step_ramp), hold, shutdown_s))
        cumulative = target

    row_re = re.compile(
        r'(<collectionProp name="\d+">\s*<stringProp name="0">)\d+(</stringProp>\s*'
        r'<stringProp name="1">)\d+(</stringProp>\s*<stringProp name="2">)\d+(</stringProp>\s*'
        r'<stringProp name="3">)\d+(</stringProp>\s*<stringProp name="4">)\d+(</stringProp>\s*</collectionProp>)'
    )
    row_iter = iter(rows)
    def repl(m):
        r = next(row_iter)
        return (m.group(1) + str(r[0]) + m.group(2) + str(r[1]) + m.group(3) + str(r[2])
                + m.group(4) + str(r[3]) + m.group(5) + str(r[4]) + m.group(6))
    new_xml, n = row_re.subn(repl, xml)
    print("  RESCALED " + str(n) + " UltimateThreadGroup row(s) -> VUsers=" + str(vusers) + " Duration=" + str(duration))
    return new_xml

def patch_spike_thread_group(xml, vusers, duration):
    # Mirrors buildSpikeThreadGroupXml() in testSuites.js EXACTLY (same baseline/ramp/peak/
    # ramp/recovery phase split, including the multi-spike formula for 2-3 cycles) -- same
    # reasoning as patch_ultimate_thread_group above: the schedule is baked as literal
    # numbers, not ${__P(...)} properties, and there's no rampup parameter since Ramp-up is
    # blocked/hidden in the UI for spike tests too.
    #
    # spike_count is NOT recomputed from the override duration -- it's read from however many
    # rows already exist in the file (baked in at generation time from the suite's SAVED
    # duration, same as STRESS_STEPS always being 5 regardless of override). Only the TIMING
    # within that fixed row count rescales here; the row count itself never changes on a
    # trigger-time override, exactly like stress.
    row_re = re.compile(
        r'(<collectionProp name="\d+">\s*<stringProp name="0">)\d+(</stringProp>\s*'
        r'<stringProp name="1">)\d+(</stringProp>\s*<stringProp name="2">)\d+(</stringProp>\s*'
        r'<stringProp name="3">)\d+(</stringProp>\s*<stringProp name="4">)\d+(</stringProp>\s*</collectionProp>)'
    )
    existing_row_count = len(row_re.findall(xml))
    spike_count = max(1, existing_row_count - 1)

    baseline_users = max(1, round(vusers * 0.10))
    spike_add = max(0, vusers - baseline_users)
    baseline_startup = 5
    baseline_hold = max(0, duration - baseline_startup)
    shutdown_s = 30

    rows = [(baseline_users, 0, baseline_startup, baseline_hold, shutdown_s)]

    if spike_count == 1:
        before_s = round(duration * 0.20)
        ramp_s = max(5, round(duration * 0.03))
        peak_s = round(duration * 0.15)
        rows.append((spike_add, before_s, ramp_s, peak_s, ramp_s))
    else:
        ramp_s = max(5, round(duration * 0.03))
        peak_s = max(5, round(duration * 0.08))
        non_baseline_per_cycle = 2 * ramp_s + peak_s
        total_baseline = max(0, duration - spike_count * non_baseline_per_cycle)
        gap_s = round(total_baseline / (spike_count + 1))
        t = 0
        for _ in range(spike_count):
            t += gap_s
            rows.append((spike_add, t, ramp_s, peak_s, ramp_s))
            t += ramp_s + peak_s + ramp_s

    row_iter = iter(rows)
    def repl(m):
        r = next(row_iter)
        return (m.group(1) + str(r[0]) + m.group(2) + str(r[1]) + m.group(3) + str(r[2])
                + m.group(4) + str(r[3]) + m.group(5) + str(r[4]) + m.group(6))
    new_xml, n = row_re.subn(repl, xml)
    print("  RESCALED " + str(n) + " spike UltimateThreadGroup row(s) (" + str(spike_count) + " spike(s)) -> VUsers=" + str(vusers) + " Duration=" + str(duration))
    return new_xml

if "UltimateThreadGroup" in content:
    # Stress/spike test plan -- the staircase/spike row values, not ThreadGroup.num_threads/
    # ramp_time/duration (those properties don't exist on this element), carry the load
    # profile. Distinguished by testname -- both use the same plugin element, just a
    # different row count/shape.
    if use_duration:
        if 'testname="Spike Thread Group"' in content:
            content = patch_spike_thread_group(content, int(users), int(duration))
        else:
            content = patch_ultimate_thread_group(content, int(users), int(duration))
    else:
        print("  WARN: stress/spike test (UltimateThreadGroup) needs Duration mode - loops override skipped")
else:
    content = sp(content, "ThreadGroup.num_threads", users)
    content = sp(content, "ThreadGroup.ramp_time", rampup)

    if use_duration:
        print("  Mode: Duration " + duration + "s")
        content = sp(content, "ThreadGroup.scheduler", "true")
        content = sp(content, "ThreadGroup.duration", duration)
        content = sp(content, "LoopController.loops", "-1")
        if 'name="ThreadGroup.duration"' not in content:
            content = content.replace("</ThreadGroup>",
                '<stringProp name="ThreadGroup.duration">' + duration + '</stringProp>\n'
                '<boolProp name="ThreadGroup.scheduler">true</boolProp>\n</ThreadGroup>')
            print("  INJECTED duration+scheduler")
    else:
        print("  Mode: Loops " + loops)
        content = sp(content, "ThreadGroup.scheduler", "false")
        content = sp(content, "LoopController.loops", loops)

with open(script, "w") as f:
    f.write(content)
print("Patch complete")
