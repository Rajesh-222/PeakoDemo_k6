import http from 'k6/http';
import { check, sleep } from 'k6';

// Runtime override: k6 run --env THREADS=100 --env DURATION=600 --env RAMP_UP=60 --env PROTOCOL=https --env URL=api.example.com --env PORT=443 script.js
const THREADS  = parseInt(__ENV.THREADS  || '100');
const RAMP_UP  = parseInt(__ENV.RAMP_UP  || '40');
const DURATION = parseInt(__ENV.DURATION || '400');
const STEP_S    = Math.round(DURATION / 5);
const STEP_RAMP = Math.min(RAMP_UP, Math.max(5, Math.round(STEP_S * 0.2)));
const STEP_HOLD = Math.max(0, STEP_S - STEP_RAMP);
const PROTOCOL = __ENV.PROTOCOL || 'https';
const URL      = __ENV.URL      || 'jsonplaceholder.typicode.com';
const PORT     = __ENV.PORT     || '443';
const BASE_URL = `${PROTOCOL}://${URL}:${PORT}`;

export const options = {
  scenarios: { stress:    { executor: 'ramping-vus', startVUs: 0, stages: [
      { duration: STEP_RAMP + 's', target: Math.round(THREADS * 1 / 5) },
      { duration: STEP_HOLD + 's', target: Math.round(THREADS * 1 / 5) },
      { duration: STEP_RAMP + 's', target: Math.round(THREADS * 2 / 5) },
      { duration: STEP_HOLD + 's', target: Math.round(THREADS * 2 / 5) },
      { duration: STEP_RAMP + 's', target: Math.round(THREADS * 3 / 5) },
      { duration: STEP_HOLD + 's', target: Math.round(THREADS * 3 / 5) },
      { duration: STEP_RAMP + 's', target: Math.round(THREADS * 4 / 5) },
      { duration: STEP_HOLD + 's', target: Math.round(THREADS * 4 / 5) },
      { duration: STEP_RAMP + 's', target: THREADS },
      { duration: STEP_HOLD + 's', target: THREADS },
      { duration: '30s', target: 0 }
    ] } },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['avg<2000']
  }
};

export default function () {
  // Get Post
  let res0 = http.get(`${BASE_URL}/posts/1`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res0, { 'Get Post status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // Create Post
  let res1 = http.post(`${BASE_URL}/posts`, `{"title":"foo","body":"bar","userId":1}`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res1, { 'Create Post status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // Update Post
  let res2 = http.put(`${BASE_URL}/posts/1`, `{"id":1,"title":"foo","body":"bar","userId":1}`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res2, { 'Update Post status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // Delete Post
  let res3 = http.del(`${BASE_URL}/posts/1`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res3, { 'Delete Post status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);
}