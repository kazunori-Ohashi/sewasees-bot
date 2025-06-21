import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 12,
  duration: '60s',
};

export default function () {
  let url = 'http://localhost:8000/discord/article';
  let payload = JSON.stringify({ user: 'test', file: 'sample.txt' });
  let params = { headers: { 'Content-Type': 'application/json' } };
  let res = http.post(url, payload, params);
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
} 