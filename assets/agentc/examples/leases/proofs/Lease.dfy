datatype State = S(now: nat, issued: nat, holder: nat, token: nat, deadline: nat)
predicate Valid(s: State) { (s.holder == 0 ==> s.token == 0 && s.deadline == 0) && (s.holder > 0 ==> s.token == s.issued && s.token > 0 && s.deadline > s.now) }
method Initial() returns (s: State)
  ensures s == S(0, 0, 0, 0, 0)
  ensures Valid(s)
{
  s := S(0, 0, 0, 0, 0);
}
method Acquire(s: State, holder: nat, ttl: nat) returns (t: State, ok: bool)
  requires Valid(s) && holder > 0 && ttl > 0
  ensures Valid(t)
  ensures ok <==> s.holder == 0
  ensures t == (if s.holder == 0 then S(s.now, s.issued + 1, holder, s.issued + 1, s.now + ttl) else s)
  ensures ok ==> t.token > s.issued
{
  ok := s.holder == 0;
  t := if ok then S(s.now, s.issued + 1, holder, s.issued + 1, s.now + ttl) else s;
}
method Release(s: State, holder: nat, token: nat) returns (t: State, ok: bool)
  requires Valid(s) && holder > 0
  ensures Valid(t)
  ensures ok <==> s.holder == holder && s.token == token
  ensures t == (if s.holder == holder && s.token == token then S(s.now, s.issued, 0, 0, 0) else s)
  ensures token < s.issued ==> t == s && !ok
{
  ok := s.holder == holder && s.token == token;
  t := if ok then S(s.now, s.issued, 0, 0, 0) else s;
}
method Advance(s: State, now: nat) returns (t: State)
  requires Valid(s) && now >= s.now
  ensures Valid(t)
  ensures t == (if s.holder > 0 && now < s.deadline then S(now, s.issued, s.holder, s.token, s.deadline) else S(now, s.issued, 0, 0, 0))
  ensures t.now >= s.now && t.issued == s.issued
{
  t := if s.holder > 0 && now < s.deadline then S(now, s.issued, s.holder, s.token, s.deadline) else S(now, s.issued, 0, 0, 0);
}
lemma LaterLeaseRejectsOldToken(s: State, oldToken: nat, holder: nat)
  requires Valid(s) && s.holder > 0 && oldToken < s.issued && holder > 0
  ensures !(s.holder == holder && s.token == oldToken)
{
}
