import ContractSpec

namespace Candidate
open Calculator

/-- Called only on nonempty digit lists after parsing checks. -/
def decimal (cs : List Char) : Nat :=
  cs.foldl (fun value c => value * 10 + (c.toNat - '0'.toNat)) 0

/-- Grammar: [0-9]+(add|sub|mul|div|+|-|*|/)[0-9]+, with complete consumption. -/
def parse (s : String) : Except CalcError Expression :=
  let chars := s.toList
  let left := chars.takeWhile asciiDigit
  let rest := chars.dropWhile asciiDigit
  let operator := rest.takeWhile (fun c => asciiLetter c || asciiOperator c)
  let right := rest.dropWhile (fun c => asciiLetter c || asciiOperator c)
  if left.isEmpty || right.isEmpty || !(right.all asciiDigit) then
    .error .invalidExpression
  else
    let op : Option Op := match String.mk operator with
      | "add" | "+" => some .add
      | "sub" | "-" => some .sub
      | "mul" | "*" => some .mul
      | "div" | "/" => some .div
      | _ => none
    match op with
    | none => .error .invalidExpression
    | some operation => .ok ⟨decimal left, operation, decimal right⟩

def evaluate (e : Expression) : Result :=
  match e.op with
  | .add => .ok ((e.left : Int) + (e.right : Int))
  | .sub => .ok ((e.left : Int) - (e.right : Int))
  | .mul => .ok ((e.left : Int) * (e.right : Int))
  | .div => if e.right = 0 then .error .divisionByZero
            else .ok ((e.left / e.right : Nat) : Int)

/-- Variant one: direct guard and pattern matching. -/
def calculate (s : String) : Result :=
  if validCharacters s then
    match parse s with
    | .error error => .error error
    | .ok expression => evaluate expression
  else .error .invalidCharacters

/-- Variant two: error-propagating pipeline. -/
def validate (s : String) : Except CalcError String :=
  if validCharacters s then .ok s else .error .invalidCharacters

def calculatePipeline (s : String) : Result :=
  Except.bind (validate s) (fun clean => Except.bind (parse clean) evaluate)

/-- Deliberately wrong: silently deletes invalid characters. -/
def badStrip (s : String) : Result :=
  calculate (String.mk (s.toList.filter allowedCharacter))

end Candidate


namespace Candidate
open Calculator

theorem invalid_rejected : InvalidInputContract calculate := by
  intro s h
  simp [calculate, h]

theorem pipeline_invalid_rejected : InvalidInputContract calculatePipeline := by
  intro s h
  simp [calculatePipeline, validate, h, Except.bind]

theorem variants_equivalent (s : String) : calculatePipeline s = calculate s := by
  cases h : validCharacters s <;> simp [calculatePipeline, validate, calculate, h, Except.bind]
  cases parse s <;> rfl

theorem success_has_valid_characters (s : String) (value : Int)
    (h : calculate s = .ok value) : validCharacters s = true := by
  cases hc : validCharacters s
  · simp [calculate, hc] at h
  · rfl

theorem arithmetic_correct : ArithmeticContract evaluate := by
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · intro a b; rfl
  · intro a b; rfl
  · intro a b; rfl
  · intro a; simp [evaluate]
  · intro a b hb; simp [evaluate, hb]

theorem parse_error_propagates (s : String) (h : validCharacters s = true)
    (hp : parse s = .error .invalidExpression) :
    calculate s = .error .invalidExpression := by
  simp [calculate, h, hp]

theorem parsed_expression_evaluated (s : String) (e : Expression)
    (h : validCharacters s = true) (hp : parse s = .ok e) :
    calculate s = evaluate e := by
  simp [calculate, h, hp]

theorem zero_division_propagates (s : String) (a : Nat)
    (h : validCharacters s = true) (hp : parse s = .ok ⟨a, .div, 0⟩) :
    calculate s = .error .divisionByZero := by
  simp [calculate, h, hp, evaluate]

/-- This candidate violates the prompt; it computes 15 from "12@add3". -/
theorem stripping_is_incorrect : ¬ InvalidInputContract badStrip := by
  intro h
  have hx := h "12@add3" (by decide)
  have hn : badStrip "12@add3" ≠ .error .invalidCharacters := by decide
  exact hn hx

-- Concrete parser/evaluator examples checked by kernel computation, not native_decide.
theorem example_add : calculate "12add3" = .ok 15 := by decide
theorem example_sub : calculate "3sub12" = .ok (-9) := by decide
theorem example_mul : calculate "12mul3" = .ok 36 := by decide
theorem example_div : calculate "12div5" = .ok 2 := by decide
theorem example_zero : calculate "12div0" = .error .divisionByZero := by decide
theorem example_symbol : calculate "12+3" = .ok 15 := by decide
theorem example_ascii_sub : calculate "3-12" = .ok (-9) := by decide
theorem example_ascii_mul : calculate "12*3" = .ok 36 := by decide
theorem example_ascii_div : calculate "12/5" = .ok 2 := by decide
theorem example_ascii_zero : calculate "12/0" = .error .divisionByZero := by decide
theorem example_forbidden : calculate "12@3" = .error .invalidCharacters := by decide
theorem example_mixed : calculate "12+add3" = .error .invalidExpression := by decide
theorem ascii_operators_allowed :
    allowedCharacter '+' = true ∧ allowedCharacter '-' = true ∧
    allowedCharacter '*' = true ∧ allowedCharacter '/' = true := by decide
theorem example_empty : calculate "" = .error .invalidExpression := by decide
theorem example_word : calculate "hello" = .error .invalidExpression := by decide
theorem example_unicode : calculate "１２add3" = .error .invalidCharacters := by decide

end Candidate
