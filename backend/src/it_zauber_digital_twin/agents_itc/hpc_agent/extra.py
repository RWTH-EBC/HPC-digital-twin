import numpy as np
import numpy.typing as npt


# needs to be a class to be serializable with pickle
class PiecewiseLinearInterpolation:
    def __init__(
        self,
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
        left: float = 0,
        right: float = 1,
    ) -> None:
        self.x = x
        self.y = y
        self.left = left
        self.right = right

    def __call__(self, x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        return np.interp(x, self.x, self.y, left=self.left, right=self.right)