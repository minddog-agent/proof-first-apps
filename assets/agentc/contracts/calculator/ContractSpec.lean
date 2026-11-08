import Std

deriving instance DecidableEq for Except

namespace Calculator

inductive CalcError where
  | invalidCharacters
  | invalidExpression
  | divisionByZero
  deriving DecidableEq, Repr

inductive Op where
  | add | sub | mul | div
  deriving DecidableEq, Repr

structure Expression where
  left : Nat
  op : Op
  right : Nat
  deriving DecidableEq, Repr

abbrev Result := Except CalcError Int

def asciiDigit (c : Char) : Bool := decide ('0' ≤ c ∧ c ≤ '9')
def asciiLetter (c : Char) : Bool :=
  decide (('a' ≤ c ∧ c ≤ 'z') ∨ ('A' ≤ c ∧ c ≤ 'Z'))
def asciiAlphanumeric (c : Char) : Bool := asciiDigit c || asciiLetter c

def asciiOperator (c : Char) : Bool := decide (c = '+' ∨ c = '-' ∨ c = '*' ∨ c = '/')
def allowedCharacter (c : Char) : Bool := asciiAlphanumeric c || asciiOperator c

def validCharacters (s : String) : Bool := s.toList.all allowedCharacter

/-- The prompt's mandatory character-validation requirement. -/
def InvalidInputContract (f : String → Result) : Prop :=
  ∀ s, validCharacters s = false → f s = .error .invalidCharacters

/-- Arithmetic meaning, independent of how expressions are evaluated. -/
def ArithmeticContract (f : Expression → Result) : Prop :=
  (∀ a b, f ⟨a, .add, b⟩ = .ok ((a : Int) + (b : Int))) ∧
  (∀ a b, f ⟨a, .sub, b⟩ = .ok ((a : Int) - (b : Int))) ∧
  (∀ a b, f ⟨a, .mul, b⟩ = .ok ((a : Int) * (b : Int))) ∧
  (∀ a, f ⟨a, .div, 0⟩ = .error .divisionByZero) ∧
  (∀ a b, b ≠ 0 → f ⟨a, .div, b⟩ = .ok ((a / b : Nat) : Int))

end Calculator

namespace Calculator
/-- A separate grammar relation; candidate parser code is not referenced. -/
def decimalSpec : List Char → Nat
  | [] => 0
  | c :: cs => (c.toNat - '0'.toNat) * 10 ^ cs.length + decimalSpec cs

def spellings : Op → List String
  | .add => ["+", "add"]
  | .sub => ["-", "sub"]
  | .mul => ["*", "mul"]
  | .div => ["/", "div"]

def Spells (s : String) (e : Expression) : Prop :=
  ∃ left right : List Char, ∃ token : String,
    left ≠ [] ∧ right ≠ [] ∧
    (∀ c ∈ left, asciiDigit c = true) ∧
    (∀ c ∈ right, asciiDigit c = true) ∧
    token ∈ spellings e.op ∧
    decimalSpec left = e.left ∧ decimalSpec right = e.right ∧
    s = String.mk (left ++ token.toList ++ right)
end Calculator
