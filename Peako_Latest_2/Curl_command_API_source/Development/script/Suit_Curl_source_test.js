import http from 'k6/http';
import { check, sleep } from 'k6';

// Runtime override: k6 run --env THREADS=100 --env DURATION=600 --env RAMP_UP=60 --env PROTOCOL=https --env URL=api.example.com --env PORT=443 script.js
const THREADS  = parseInt(__ENV.THREADS  || '10');
const RAMP_UP  = parseInt(__ENV.RAMP_UP  || '5');
const DURATION = parseInt(__ENV.DURATION || '100');
const PROTOCOL = __ENV.PROTOCOL || 'https';
const URL      = __ENV.URL      || 'jsonplaceholder.typicode.com';
const PORT     = __ENV.PORT     || '443';
const BASE_URL = `${PROTOCOL}://${URL}:${PORT}`;

export const options = {
  scenarios: { load:      { executor: 'constant-vus',       vus: THREADS, duration: DURATION + 's' } },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
    http_reqs: ['rate>50']
  }
};

export default function () {
  // cURL Request
  let res0 = http.post(`${BASE_URL}/posts`, `{"title":"foo","body":"bar","userId":1}`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res0, { 'cURL Request status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);
}