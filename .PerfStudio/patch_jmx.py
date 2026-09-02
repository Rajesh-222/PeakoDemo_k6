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

def patch_ultimate_thread_group(xml, vusers, rampup, duration):
    # Mirrors buildUltimateThreadGroupXml() in testSuites.js EXACTLY (same 5-step
    # staircase formula) -- a stress test's schedule is baked as literal row numbers at
    # script-generation time, not as ${__P(...)} properties like the flat ThreadGroup,
    # so overriding VUsers/Ramp-up/Duration at CI-trigger time means recomputing every
    # row here rather than a simple property-value substitution.
    steps = 5
    shutdown_s = 30
    step_budget = duration / steps
    step_ramp = min(rampup, max(5, round(step_budget * 0.2)))
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
    print("  RESCALED " + str(n) + " UltimateThreadGroup row(s) -> VUsers=" + str(vusers) + " Ramp=" + str(rampup) + " Duration=" + str(duration))
    return new_xml

if "UltimateThreadGroup" in content:
    # Stress test plan -- the staircase row values, not ThreadGroup.num_threads/ramp_time/
    # duration (those properties don't exist on this element), carry the load profile.
    if use_duration:
        content = patch_ultimate_thread_group(content, int(users), int(rampup), int(duration))
    else:
        print("  WARN: stress test (UltimateThreadGroup) needs Duration mode - loops override skipped")
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
