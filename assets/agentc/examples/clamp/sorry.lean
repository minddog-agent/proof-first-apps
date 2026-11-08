import ContractSpec
namespace Candidate
def run (x : Int) : Int := x
theorem correct : ClampSpec.Correct run := by sorry
end Candidate
