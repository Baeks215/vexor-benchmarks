import Data.Colour.RGBSpace (uncurryRGB)
import Data.Colour.RGBSpace.HSL (hsl)
import Data.Colour.SRGB (sRGB)
import Diagrams.Backend.SVG (B, renderSVG)
import Diagrams.Prelude

steps, revolutions :: Int
steps = 100
revolutions = 2

headSize, maxDist :: Double
headSize = 80
maxDist = 400

-- make_circle(max_steps)(i): Circle(radius) >> fill(color) >> move(x, y)
makeCircle :: Int -> Int -> Diagram B
makeCircle maxSteps i =
  circle radius # fc color # lw none # translate (r2 (x, y))
 where
  frac = fromIntegral i / fromIntegral maxSteps
  radius = headSize * frac
  color = uncurryRGB sRGB (hsl (frac * 360) 0.9 0.5)
  angle = 2 * pi * fromIntegral revolutions * frac
  x = cos angle * maxDist * frac
  y = sin angle * maxDist * frac

-- make_snake(): Group(map(make_circle(steps))([1..steps]))
makeSnake :: Diagram B
makeSnake = mconcat (map (makeCircle steps) [1 .. steps])

main :: IO ()
main = do
  renderSVG "snake.svg" (mkWidth 1000) makeSnake
  putStrLn "Saved snake.svg"
