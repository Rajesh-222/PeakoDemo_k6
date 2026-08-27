import http from 'k6/http';
import { check, sleep } from 'k6';

// Runtime override: k6 run --env THREADS=100 --env DURATION=600 --env RAMP_UP=60 --env PROTOCOL=https --env URL=api.example.com --env PORT=443 script.js
const THREADS  = parseInt(__ENV.THREADS  || '10');
const RAMP_UP  = parseInt(__ENV.RAMP_UP  || '30');
const DURATION = parseInt(__ENV.DURATION || '100');
const PROTOCOL = __ENV.PROTOCOL || 'https';
const URL      = __ENV.URL      || 'dummyjson.com';
const PORT     = __ENV.PORT     || '443';
const BASE_URL = `${PROTOCOL}://${URL}:${PORT}`;

export const options = {
  scenarios: { load:      { executor: 'constant-vus',       vus: THREADS, duration: DURATION + 's' } },
  thresholds: {
    http_req_failed: ['rate<0.01']
  }
};

export default function () {
  // Login
  let res0 = http.post(`${BASE_URL}/auth/login`, `{
	"username": "emilys",
    "password": "emilyspass",
    "expiresInMins": 30
}`, {
    headers: {
        'Content-Type': `application/json`,
    },
  });
  check(res0, { 'Login status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  const accessToken = res0.json()?.accessToken;
  const refreshToken = res0.json()?.refreshToken;
  sleep(1);

  // getUserDetails
  let res1 = http.get(`${BASE_URL}/auth/me`, {
    headers: {
        'Content-Type': `application/json`,
        'Authorization': `Bearer ${accessToken}`,
    },
  });
  check(res1, { 'getUserDetails status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // getUserById
  let res2 = http.get(`${BASE_URL}/users/1`, {
    headers: {
        'Content-Type': `application/json`,
        'Authorization': `Bearer ${accessToken}`,
    },
  });
  check(res2, { 'getUserById status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);

  // getUserByName
  let res3 = http.get(`${BASE_URL}/users/search?q=emilys`, {
    headers: {
        'Content-Type': `application/json`,
        'Authorization': `Bearer ${accessToken}`,
    },
  });
  check(res3, { 'getUserByName status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
  sleep(1);
}