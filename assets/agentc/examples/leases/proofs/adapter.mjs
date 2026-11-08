// Tested-only boundary. All state transitions run compiled Dafny.
const nat = (x, positive = false) => {
  if (typeof x !== 'bigint' || x < (positive ? 1n : 0n)) throw new TypeError('Expected nonnegative BigInt (positive for holder/ttl)');
  return new BigNumber(x.toString());
};
export function createLease() {
  let state = _module.__default.Initial();
  const snapshot = () => Object.fromEntries(['now','issued','holder','token','deadline'].map(k => [k, BigInt(state['dtor_' + k].toFixed(0))]));
  return Object.freeze({
    snapshot,
    acquire(holder, ttl) {
      const [next, ok] = _module.__default.Acquire(state, nat(holder,true), nat(ttl,true));
      state = next; return {ok, state:snapshot()};
    },
    release(holder, token) {
      const [next, ok] = _module.__default.Release(state, nat(holder,true), nat(token));
      state = next; return {ok, state:snapshot()};
    },
    advance(now) {
      const n = nat(now);
      if (n.lt(state.dtor_now)) throw new RangeError('Clock cannot move backwards');
      state = _module.__default.Advance(state,n); return snapshot();
    }
  });
}
