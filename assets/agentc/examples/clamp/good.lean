import ContractSpec
namespace Candidate
def run (x : Int) : Int := if x < 0 then 0 else if 100 < x then 100 else x
theorem correct : ClampSpec.Correct run := by
  intro x
  simp only [run]
  split <;> (try split) <;> omega
end Candidate
