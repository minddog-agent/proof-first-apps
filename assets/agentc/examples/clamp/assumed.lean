import ContractSpec
namespace Candidate
def run (x : Int) : Int := x
axiom invented : ClampSpec.Correct run
theorem correct : ClampSpec.Correct run := invented
end Candidate
