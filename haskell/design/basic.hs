import Diagrams.Backend.SVG.CmdLine
import Diagrams.Prelude

-- Simple circle with radius 100
myCircle :: Diagram B
myCircle = circle 100

-- Export as SVG
main :: IO ()
main = mainWith myCircle
