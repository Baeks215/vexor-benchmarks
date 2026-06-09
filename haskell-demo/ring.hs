import Diagrams.Backend.SVG.CmdLine
import Diagrams.Prelude

n :: Int
n = 6
ringRadius :: Double
ringRadius = 50
spreadRadius :: Double
spreadRadius = 100

makeDot :: Int -> Diagram B
makeDot i =
  circle ringRadius # lw 2 # translate (r2 (x, y))
 where
  angle = 2 * pi * fromIntegral i / fromIntegral n
  x = spreadRadius * cos angle
  y = spreadRadius * sin angle

rings :: Diagram B
rings = mconcat [makeDot i | i <- [0 .. n - 1]]

main :: IO ()
main = mainWith rings
