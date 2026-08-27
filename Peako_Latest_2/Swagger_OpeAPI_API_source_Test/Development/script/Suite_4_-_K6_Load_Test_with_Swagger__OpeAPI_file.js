import http from 'k6/http';
import { check, sleep } from 'k6';

// Runtime override: k6 run --env THREADS=100 --env DURATION=600 --env RAMP_UP=60 --env PROTOCOL=https --env URL=api.example.com --env PORT=443 script.js
const THREADS  = parseInt(__ENV.THREADS  || '10');
const RAMP_UP  = parseInt(__ENV.RAMP_UP  || '5');
const DURATION = parseInt(__ENV.DURATION || '200');
const PROTOCOL = __ENV.PROTOCOL || 'https';
const URL      = __ENV.URL      || 'jsonplaceholder.typicode.com';
const PORT     = __ENV.PORT     || '443';
const BASE_URL = `${PROTOCOL}://${URL}:${PORT}`;

export const options = {
  scenarios: { load:      { executor: 'constant-vus',       vus: THREADS, duration: DURATION + 's' } },
  thresholds: {
    http_req_failed: ['rate<0.01']
  }
};

export default function () {
  // createPost
  let res0 = http.post(`${BASE_URL}/posts`, `{"title":"foo","body":"bar","userId":1}`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res0, { 'createPost status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // getPost
  let res1 = http.get(`${BASE_URL}/posts/1`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res1, { 'getPost status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // updatePost
  let res2 = http.put(`${BASE_URL}/posts/1`, `{"id":1,"title":"foo","body":"bar","userId":1}`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res2, { 'updatePost status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // deletePost
  let res3 = http.del(`${BASE_URL}/posts/1`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res3, { 'deletePost status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);
}