import Std
namespace ClampSpec
def Correct (f : Int → Int) : Prop :=
  ∀ x, (0 ≤ f x ∧ f x ≤ 100) ∧
    (x < 0 → f x = 0) ∧
    (0 ≤ x → x ≤ 100 → f x = x) ∧
    (100 < x → f x = 100)
end ClampSpec
