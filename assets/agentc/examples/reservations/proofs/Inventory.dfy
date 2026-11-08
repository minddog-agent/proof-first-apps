datatype Seat = Seat(status:nat,owner:nat,token:nat,expires:nat)
datatype Command = Cmd(id:string,kind:nat,seat:nat,owner:nat,token:nat,ttl:nat,expected:nat)
datatype Inventory = Inv(now:nat,version:nat,seats:seq<Seat>,seen:map<string,Command>)
predicate Valid(s:Inventory) { 1<=|s.seats|<=100 && forall i :: 0<=i<|s.seats| ==> s.seats[i].status<=2 && s.seats[i].owner<2 && (s.seats[i].status==1 ==> s.seats[i].expires>s.now) }
function Count(xs:seq<Seat>,status:nat):nat { if |xs|==0 then 0 else (if xs[0].status==status then 1 else 0)+Count(xs[1..],status) }
lemma Partition(xs:seq<Seat>)
 requires forall i :: 0<=i<|xs| ==> xs[i].status<=2
 ensures Count(xs,0)+Count(xs,1)+Count(xs,2)==|xs|
 ensures Count(xs,1)+Count(xs,2)<=|xs|
 decreases |xs|
{if |xs|>0 {Partition(xs[1..]);}}
method Initial(capacity:nat) returns (s:Inventory)
 requires 1<=capacity<=100
 ensures Valid(s) && s.now==0 && s.version==0 && |s.seats|==capacity && |s.seen|==0
 ensures forall i :: 0<=i<capacity ==> s.seats[i]==Seat(0,0,0,0)
{
 var xs:seq<Seat>:=[];
 while |xs|<capacity
  invariant |xs|<=capacity
  invariant forall i :: 0<=i<|xs| ==> xs[i]==Seat(0,0,0,0)
  decreases capacity-|xs|
 {xs:=xs+[Seat(0,0,0,0)];}
 s:=Inv(0,0,xs,map[]);
}
method Expire(xs:seq<Seat>,now:nat) returns (ys:seq<Seat>)
 requires forall i :: 0<=i<|xs| ==> xs[i].status<=2 && xs[i].owner<2
 ensures |ys|==|xs|
 ensures forall i :: 0<=i<|xs| ==> ys[i]==(if xs[i].status==1 && xs[i].expires<=now then xs[i].(status:=0) else xs[i])
 ensures forall i :: 0<=i<|ys| ==> ys[i].status<=2 && ys[i].owner<2 && (ys[i].status==1 ==> ys[i].expires>now)
 decreases |xs|
{
 if |xs|==0 {ys:=[];}
 else {var tail:=Expire(xs[1..],now);ys:=[if xs[0].status==1 && xs[0].expires<=now then xs[0].(status:=0) else xs[0]]+tail;}
}
method Step(s:Inventory,c:Command) returns (t:Inventory,result:nat)
 requires Valid(s) && c.kind<=3 && c.seat<|s.seats| && c.owner<2
 requires c.kind==0 || c.kind==3 ==> 1<=c.ttl<=3600
 ensures Valid(t) && |t.seats|==|s.seats|
 ensures Count(t.seats,0)+Count(t.seats,1)+Count(t.seats,2)==|s.seats|
 ensures Count(t.seats,1)+Count(t.seats,2)<=|s.seats|
 ensures c.id in s.seen ==> t==s && result==(if s.seen[c.id]==c then 3 else 4)
 ensures c.id !in s.seen && c.expected!=s.version ==> t==s && result==5
 ensures c.id !in s.seen && c.expected==s.version ==> t.version==s.version+1 && t.seen==s.seen[c.id:=c]
 ensures c.id !in s.seen && c.expected==s.version && c.kind==0 ==> (result==0 <==> s.seats[c.seat].status==0)
 ensures c.id !in s.seen && c.expected==s.version && c.kind==0 && s.seats[c.seat].status==0 ==> t.seats==s.seats[c.seat:=Seat(1,c.owner,s.version+1,s.now+c.ttl)]
 ensures c.id !in s.seen && c.expected==s.version && (c.kind==1 || c.kind==2) ==> (result==0 <==> s.seats[c.seat].status==1 && s.seats[c.seat].owner==c.owner && s.seats[c.seat].token==c.token)
 ensures c.id !in s.seen && c.expected==s.version && c.kind==1 && result==0 ==> s.now<s.seats[c.seat].expires && t.seats==s.seats[c.seat:=s.seats[c.seat].(status:=2)]
 ensures c.id !in s.seen && c.expected==s.version && c.kind==2 && result==0 ==> t.seats==s.seats[c.seat:=s.seats[c.seat].(status:=0)]
 ensures c.kind!=3 ==> t.now==s.now
 ensures result!=0 ==> t.seats==s.seats && t.now==s.now
 ensures c.id !in s.seen && c.expected==s.version && c.kind==3 ==> result==0 && t.now==s.now+c.ttl && (forall i :: 0<=i<|s.seats| ==> t.seats[i]==(if s.seats[i].status==1 && s.seats[i].expires<=t.now then s.seats[i].(status:=0) else s.seats[i]))
{
 t:=s;result:=0;
 if c.id in s.seen {result:=if s.seen[c.id]==c then 3 else 4;Partition(t.seats);return;}
 if c.expected!=s.version {result:=5;Partition(t.seats);return;}
 t:=s.(version:=s.version+1,seen:=s.seen[c.id:=c]);
 var seat:=s.seats[c.seat];
 if c.kind==0 {
  if seat.status!=0 {result:=1;}
  else {t:=t.(seats:=s.seats[c.seat:=Seat(1,c.owner,s.version+1,s.now+c.ttl)]);}
 } else if c.kind==1 || c.kind==2 {
  if seat.status!=1 || seat.owner!=c.owner || seat.token!=c.token {result:=2;}
  else {t:=t.(seats:=s.seats[c.seat:=seat.(status:=if c.kind==1 then 2 else 0)]);}
 } else {var seats:=Expire(s.seats,s.now+c.ttl);t:=t.(now:=s.now+c.ttl,seats:=seats);}
 Partition(t.seats);
}
method Retry(s:Inventory,c:Command) returns (first:Inventory,second:Inventory)
 requires Valid(s) && c.kind<=3 && c.seat<|s.seats| && c.owner<2
 requires c.kind==0 || c.kind==3 ==> 1<=c.ttl<=3600
 ensures Valid(first) && second==first
{
 var r;first,r:=Step(s,c);var r2;second,r2:=Step(first,c);
}
method CompetingBuyers(s:Inventory,a:Command,b:Command) returns (first:Inventory,second:Inventory)
 requires Valid(s) && a.kind==0 && b.kind==0 && a.seat==b.seat && a.seat<|s.seats|
 requires a.owner<2 && b.owner<2 && a.owner!=b.owner
 requires 1<=a.ttl<=3600 && 1<=b.ttl<=3600
 requires a.id !in s.seen && b.id !in s.seen && a.id!=b.id
 requires a.expected==s.version && b.expected==s.version && s.seats[a.seat].status==0
 ensures Valid(first) && |first.seats|==|s.seats| && second==first && first.seats[a.seat].status==1 && first.seats[a.seat].owner==a.owner
{
 var r;first,r:=Step(s,a);var q;second,q:=Step(first,b);
 assert r==0 && q==5;
 assert second==first && second.seats[a.seat].owner==a.owner;
}
