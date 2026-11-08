import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createLease} from '../lib/verified/core.mjs';
test('acquire, competing holder, matching release, stale release across reacquisition',()=>{
 const l=createLease();
 assert.equal(l.acquire(1n,10n).ok,true);
 assert.equal(l.acquire(2n,10n).ok,false);
 assert.equal(l.release(2n,1n).ok,false);
 assert.equal(l.release(1n,0n).ok,false);
 assert.equal(l.release(1n,1n).ok,true);
 assert.equal(l.acquire(1n,10n).state.token,2n);
 assert.equal(l.release(1n,1n).ok,false);
 assert.equal(l.snapshot().token,2n);
});
test('exact expiry boundary and reacquisition; old release preserves later lease',()=>{
 const l=createLease();l.acquire(5n,10n);
 assert.equal(l.advance(9n).holder,5n);
 assert.equal(l.advance(10n).holder,0n);
 assert.equal(l.release(5n,1n).ok,false);
 assert.equal(l.acquire(5n,2n).state.token,2n);
 assert.equal(l.release(5n,1n).ok,false);
 assert.equal(l.advance(12n).holder,0n);
});
test('invalid inputs, nondecreasing clock, detached snapshots and arbitrary precision',()=>{
 const l=createLease();const big=2n**100n;
 for(const x of [1,'1',-1n,null,NaN]) assert.throws(()=>l.advance(x));
 assert.throws(()=>l.acquire(0n,1n));assert.throws(()=>l.acquire(1n,0n));
 l.advance(big);l.advance(big);assert.throws(()=>l.advance(big-1n));
 l.acquire(big,big);const s=l.snapshot();assert.equal(s.deadline,2n*big);
 s.holder=0n;assert.equal(l.snapshot().holder,big);
 assert.equal(l.advance(2n*big-1n).holder,big);assert.equal(l.advance(2n*big).holder,0n);
});
test('independent reference over 2000 seeded mixed commands',()=>{
 const l=createLease();let s={now:0n,issued:0n,holder:0n,token:0n,deadline:0n};let seed=17;
 const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed;};
 for(let i=0;i<2000;i++){
  const kind=rand()%3,holder=BigInt(rand()%3+1),token=BigInt(rand()%25),ttl=BigInt(rand()%10+1);
  if(kind===0){const ok=s.holder===0n; if(ok){s.issued++;s.holder=holder;s.token=s.issued;s.deadline=s.now+ttl;}assert.equal(l.acquire(holder,ttl).ok,ok);}
  if(kind===1){const ok=s.holder===holder&&s.token===token;if(ok){s.holder=0n;s.token=0n;s.deadline=0n;}assert.equal(l.release(holder,token).ok,ok);}
  if(kind===2){s.now+=BigInt(rand()%8);if(s.now>=s.deadline){s.holder=0n;s.token=0n;s.deadline=0n;}l.advance(s.now);}
  assert.deepEqual(l.snapshot(),s);
 }
});
