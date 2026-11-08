function Total(ds: seq<nat>): nat
  decreases |ds|
{
  if |ds| == 0 then 0 else Total(ds[..|ds|-1]) + ds[|ds|-1]
}
method Build(ds: seq<nat>) returns (ends: seq<nat>)
  ensures |ends| == |ds| + 1
  ensures ends[0] == 0
  ensures forall j :: 0 <= j < |ds| ==> ends[j+1] == ends[j] + ds[j]
  ensures forall j :: 0 <= j < |ds| ==> ends[j] <= ends[j+1]
  ensures ends[|ds|] == Total(ds)
{
  ends := [0];
  var i := 0;
  while i < |ds|
    invariant 0 <= i <= |ds|
    invariant |ends| == i+1
    invariant ends[0] == 0
    invariant forall j :: 0 <= j < i ==> ends[j+1] == ends[j] + ds[j]
    invariant forall j :: 0 <= j < i ==> ends[j] <= ends[j+1]
    invariant ends[i] == Total(ds[..i])
  {
    assert ds[..i+1][..i] == ds[..i];
    ends := ends + [ends[i] + ds[i]];
    i := i+1;
  }
  assert ds[..i] == ds;
}
