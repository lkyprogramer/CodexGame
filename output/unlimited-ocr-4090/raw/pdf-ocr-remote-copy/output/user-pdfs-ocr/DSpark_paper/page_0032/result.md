Appendices
A. Counterexample: Selection Bias Without Early-Stopping
We provide a simple counterexample to illustrate how an offline global search, i.e., operating without the break condition in Algorithm 1, violates the non-anticipating property required by lossless speculative decoding. Formally, the admission event for the \(k\)-th draft token, \(\ell_r \geq k\), must be determined by scheduler-visible information available before the token \(x_{r,k}\) is sampled. It must not depend on the realization of \(x_{r,k}\) itself. Consider a scenario with a single request \((R = 1)\) and maximum draft length \((y = 2)\). Suppose the pre-token confidence for the first position is \(a_1 = 0.8\), and the profiled capacity curve is
\[
\operatorname{SPS} (1) = 1. 0, \quad \operatorname{SPS} (2) = 0. 5, \quad \operatorname{SPS} (3) = 0. 4 5.
\]
The expected throughputs for verifying 0 and 1 draft tokens are
\[
\begin{array}{l} \Theta_ {0} = 1 \cdot \operatorname{SPS} (1) = 1. 0, \\ \Theta_ {1} = (1 + 0. 8) \cdot \mathrm{SPS} (2) = 0. 9. \\ \end{array}
\]
Without early-stopping, the scheduler proceeds to evaluate  \( \Theta_{2} \)  before committing any admission decisions. Because the Markov confidence head uses the previously sampled token, the next confidence score  \( c_{2} \)  explicitly depends on the realization of  \( x_{1} \) . Consequently, the second-prefix survival probability
\[
\alpha_ {2} = \alpha_ {1} c _ {2}
\]
also depends on \( x_{1} \). Consider two possible realizations of \( x_{1} \):
- Case 1 (\(x_{1}\) yields a high \(c_{2}\)): Suppose \(x_{1}\) results in \(c_{2} = 0.9\). Then
\[
\alpha_ {2} = 0. 8 \times 0. 9 = 0. 7 2.
\]
The expected throughput for length 2 is
\[
\Theta_ {2} = (1 + 0. 8 + 0. 7 2) \times 0. 4 5 = 1. 1 3 4.
\]
Since \(\Theta_{2}\) is the global maximum among \(\{1.0, 0.9, 1.134\}\), the scheduler returns \(\ell = 2\). The first token \(x_{1}\) is admitted into the verification prefix.
- Case 2 (\(x_{1}\) yields a low \(c_{2}\)): Suppose \(x_{1}\) results in \(c_{2} = 0\). Then
\[
a _ {2} = 0.
\]
The expected throughput for length 2 is
\[
\Theta_ {2} = (1 + 0. 8 + 0) \times 0. 4 5 = 0. 8 1.
\]
Here, the global maximum remains \(\Theta_0 = 1.0\), so the scheduler returns \(\ell = 0\). The first token \(x_{1}\) is not admitted into the verification prefix.
Thus, the admission of the first draft token dynamically depends on the value of the first draft token itself. This retrospective dependence introduces selection bias: the scheduler favors tokens that lead to highly confident continuations, even though the admission decision for \( x_{1} \) should have been made before observing \( x_{1} \). We now make the distributional bias explicit. Let the vocabulary be \( \{A, B\} \), and consider the target and draft distributions at the first position:
\[
p _ {1} (A) = 0. 7, \quad p _ {1} (B) = 0. 3,
\]
32