import test from 'node:test';import assert from 'node:assert/strict';
import {createInventory} from '../lib/verified/core.mjs';
import {replay,command,scenario} from '../lib/inventory.mjs';
const cmd=(id,kind=0,seat=0,owner=0,expected=0,token=0,ttl=120)=>command(id,kind,seat,owner,expected,token,ttl);
test('initial partition and validation',()=>{for(const n of [1,12,100]){const s=createInventory(n).snapshot();assert.equal(s.available,n);assert.equal(s.held+s.sold,0);}for(const n of [0,101,1.5,NaN,'1'])assert.throws(()=>createInventory(n));});
test('both commit orders produce one last-seat winner; refreshed loser cannot overwrite',()=>{
 for(const order of [[0,1],[1,0]]){const d=scenario('race'),e=d.queue;let s=replay(1,order.map(i=>e[i]));assert.equal(s.held,1);assert.equal(s.seats[0].owner,order[0]);assert.equal(s.trace[1].status,'stale_version');s=replay(1,[e[order[0]],e[order[1]],{...e[order[1]],expected:1}]);assert.equal(s.trace[2].status,'unavailable');assert.equal(s.seats[0].owner,order[0]);}
});
test('confirmation before deadline succeeds and sold seats never expire or cancel',()=>{
 const s=replay(1,[cmd('r'),cmd('clock',3,0,0,1,0,119),cmd('c',1,0,0,2,1),cmd('clock2',3,0,0,3,0,3600),cmd('cancel',2,0,0,4,1)]);assert.equal(s.sold,1);assert.equal(s.trace[2].status,'applied');assert.equal(s.trace[4].status,'invalid_hold');
});
test('expiration at equality releases hold; confirmation cannot resurrect it',()=>{
 const d=scenario('expiry');const s=replay(1,[...d.events,d.queue[1],d.queue[0],{...d.queue[0],expected:2}]);assert.equal(s.available,1);assert.equal(s.sold,0);assert.equal(s.trace[2].status,'stale_version');assert.equal(s.trace[3].status,'invalid_hold');
});
test('owner and token checks prevent unauthorized and obsolete claims',()=>{
 const es=[cmd('r'),cmd('wrongowner',1,0,1,1,1),cmd('wrongtoken',1,0,0,2,99),cmd('cancel',2,0,0,3,1),cmd('newhold',0,0,0,4),cmd('oldtoken',1,0,0,5,1),cmd('newtoken',1,0,0,6,5)];const s=replay(1,es);assert.deepEqual(s.trace.map(t=>t.status),['applied','invalid_hold','invalid_hold','applied','applied','invalid_hold','applied']);assert.equal(s.sold,1);assert.equal(s.seats[0].token,5);
});
test('duplicate and conflicting IDs do not change state; stale retries remain retryable',()=>{
 const e=createInventory(1);const c=cmd('r');e.apply(c);const before=e.snapshot();assert.equal(e.apply(c).status,'duplicate');assert.deepEqual(e.snapshot(),before);assert.equal(e.apply({...c,owner:1}).status,'conflict');assert.deepEqual(e.snapshot(),before);
 const c2=cmd('confirm',1,0,0,0,1);assert.equal(e.apply(c2).status,'stale_version');assert.equal(e.apply({...c2,expected:1}).status,'applied');
});
test('invalid commands fail closed; snapshots are detached',()=>{
 const e=createInventory(2),before=e.snapshot();for(const c of [null,{...cmd('x'),id:'x\n'},{...cmd('x'),kind:4},{...cmd('x'),seat:2},{...cmd('x'),owner:2},{...cmd('x'),token:-1},{...cmd('x'),expected:Infinity},{...cmd('x'),ttl:0},{...cmd('x'),ttl:3601}]){assert.throws(()=>e.apply(c));assert.deepEqual(e.snapshot(),before);}before.seats[0].status='sold';assert.equal(e.snapshot().sold,0);assert.throws(()=>replay(1,{}));assert.throws(()=>replay(1,Array(10001)));assert.equal(scenario('empty').capacity,12);
});
// Independent object-based reference; does not call generated functions.
function reference(capacity){let now=0,version=0,seats=Array.from({length:capacity},(_,id)=>({id,status:'available',owner:0,token:0,expires:0}));const seen=new Map();return c=>{let status='applied';const sig=JSON.stringify(c);if(seen.has(c.id))status=seen.get(c.id)===sig?'duplicate':'conflict';else if(c.expected!==version)status='stale_version';else{seen.set(c.id,sig);version++;const s=seats[c.seat];if(c.kind===0){if(s.status!=='available')status='unavailable';else seats[c.seat]={id:c.seat,status:'held',owner:c.owner,token:version,expires:now+c.ttl};}else if(c.kind===3){now+=c.ttl;seats=seats.map(s=>s.status==='held'&&s.expires<=now?{...s,status:'available'}:s);}else{if(s.status!=='held'||s.owner!==c.owner||s.token!==c.token)status='invalid_hold';else seats[c.seat]={...s,status:c.kind===1?'sold':'available'};}}return {status,snapshot:{now,version,seats:structuredClone(seats),available:seats.filter(s=>s.status==='available').length,held:seats.filter(s=>s.status==='held').length,sold:seats.filter(s=>s.status==='sold').length}};};}
test('seeded mixed histories match independent reference after every command',()=>{
 for(const seed of [1,17,919]){let n=seed;const engine=createInventory(8),ref=reference(8),history=[];const rng=()=>{n=(n*1664525+1013904223)>>>0;return n;};for(let i=0;i<500;i++){const s=engine.snapshot(),seat=rng()%8;let c=cmd('e'+i,rng()%4,seat,rng()%2,rng()%5===0?Math.max(0,s.version-1):s.version,s.seats[seat].token,rng()%180+1);if(i>0&&i%19===0)c=history[i-1];history.push(c);const actual=engine.apply(c);assert.deepEqual(actual,ref(c));assert.equal(actual.snapshot.available+actual.snapshot.held+actual.snapshot.sold,8);}}
});
