// Trusted conversion boundary; all inventory decisions execute compiled Dafny.
export function createInventory(capacity=12){
 if(!Number.isInteger(capacity)||capacity<1||capacity>100)throw Error('Capacity must be 1–100 seats');
 let state=_module.__default.Initial(new BigNumber(capacity));
 const integer=x=>Number.isSafeInteger(x)&&x>=0;
 const snapshot=()=>({now:state.dtor_now.toNumber(),version:state.dtor_version.toNumber(),seats:Array.from(state.dtor_seats,(s,i)=>({id:i,status:['available','held','sold'][s.dtor_status.toNumber()],owner:s.dtor_owner.toNumber(),token:s.dtor_token.toNumber(),expires:s.dtor_expires.toNumber()})),available:_module.__default.Count(state.dtor_seats,new BigNumber(0)).toNumber(),held:_module.__default.Count(state.dtor_seats,new BigNumber(1)).toNumber(),sold:_module.__default.Count(state.dtor_seats,new BigNumber(2)).toNumber()});
 return {snapshot,apply(c){
  if(!c||typeof c.id!=='string'||c.id.trim()!==c.id||!/^[A-Za-z0-9_-]{1,64}$/.test(c.id)||!['kind','seat','owner','token','ttl','expected'].every(k=>integer(c[k]))||c.kind>3||c.seat>=capacity||c.owner>1||((c.kind===0||c.kind===3)&&(c.ttl<1||c.ttl>3600))||c.expected>10000||c.token>10000||state.dtor_version.gte(10000))throw Error('Invalid command or 10,000-command simulation limit reached');
  const cmd=_module.Command.create_Cmd(_dafny.Seq.UnicodeFromString(c.id),...['kind','seat','owner','token','ttl','expected'].map(k=>new BigNumber(c[k])));
  const [next,result]=_module.__default.Step(state,cmd);state=next;
  return {status:['applied','unavailable','invalid_hold','duplicate','conflict','stale_version'][result.toNumber()],snapshot:snapshot()};
 }};
}
