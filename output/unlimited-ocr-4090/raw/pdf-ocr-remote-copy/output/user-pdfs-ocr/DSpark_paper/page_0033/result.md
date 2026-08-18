\[
p _ {\mathrm{d}} (A) = 0. 5, \qquad p _ {\mathrm{d}} (B) = 0. 5.
\]
The standard speculative acceptance probability at the first position is
\[
\sum_ {x \in \{A, B \}} \min \left(p _ {1} (x), p _ {\mathrm{d}} (x)\right) = \min (0. 7, 0. 5) + \min (0. 3, 0. 5) = 0. 8,
\]
matching the assumed value  \( (a_{1}=0.8) \) . Suppose the retrospective scheduler behaves as above:  \( x_{1}=A \)  yields a high continuation confidence and hence  \( \ell=2 \) , while  \( x_{1}=B \)  yields a low continuation confidence and hence  \( \ell=0 \) . Then the first output token is distributed as follows. If  \( x_{1}=A \) , the draft token is admitted and accepted with probability
\[
\min \left(1, \frac {p _ {\mathrm{t}} (A)}{p _ {\mathrm{d}} (A)}\right) = \min \left(1, \frac {0 . 7}{0 . 5}\right) = 1,
\]
so the output token is A. If  \( x_{1} = B \) , the draft token is not admitted; the target model instead generates a fresh token from  \( p_{t} \) . Therefore,
\[
\operatorname * {P r} (Y = A) = \operatorname * {P r} (x _ {1} = A) \cdot 1 + \operatorname * {P r} (x _ {1} = B) \cdot p _ {\mathrm{t}} (A) = 0. 5 + 0. 5 \times 0. 7 = 0. 8 5,
\]
and hence
\[
\operatorname * {P r} (Y = B) = 0. 1 5.
\]
This output distribution ((0.85, 0.15)) differs from the target distribution ((0.7, 0.3)), proving that the retrospective scheduler is not lossless. The early-stopping mechanism prevents this issue in the causal greedy scheduler. Since \(\Theta_1 < \Theta_0\), the scheduler halts immediately and returns \(\ell = 0\) before evaluating any continuation-dependent quantity such as \(c_2\). The admission decision for the first position therefore depends only on pre-token information and cannot be biased by the realization of \(x_1\). This restores the non-anticipating property required by the standard losslessness argument.
33