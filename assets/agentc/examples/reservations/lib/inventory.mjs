import {createInventory} from './verified/core.mjs';
export const names=['Alex','Sam'];
export const actions=['Reserve','Confirm','Cancel','Advance clock'];
export function replay(capacity,events){
 if(!Array.isArray(events)||events.length>10000)throw Error('At most 10,000 commands are supported');
 const engine=createInventory(capacity),trace=[];
 for(const c of events){const before=engine.snapshot();const r=engine.apply(c);trace.push({...c,status:r.status,beforeVersion:before.version,afterVersion:r.snapshot.version,now:r.snapshot.now});}
 return {...engine.snapshot(),trace};
}
export function command(id,kind,seat,owner,expected,token=0,ttl=120){return {id,kind,seat,owner,token,ttl,expected};}
export function scenario(name){
 if(name==='race')return {capacity:1,events:[],queue:[command('alex_hold',0,0,0,0),command('sam_hold',0,0,1,0)]};
 if(name==='expiry')return {capacity:1,events:[command('hold',0,0,0,0)],queue:[command('confirm',1,0,0,1,1),command('expire',3,0,0,1,0,120)]};
 return {capacity:12,events:[],queue:[]};
}
