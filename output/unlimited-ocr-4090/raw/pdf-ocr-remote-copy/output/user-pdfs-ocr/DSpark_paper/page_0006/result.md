the anchor itself as the first prediction position, so \(\gamma\) input tokens (anchor + \(\gamma - 1\) masks) yield \(\gamma\) draft logits. This reduces draft computation while maintaining similar draft quality.
Sequential stage. The sequential stage supplements the base logits with a prefix-dependent transition bias \( B_{k}(x_0, x_{<k}, x_k) \), allowing each draft position to condition on previously sampled tokens within the block. Rather than defining a globally normalized energy model, the sequential stage induces a causal block distribution through an autoregressive factorization:
\[
P (X \mid x _ {0}) = \prod_ {k = 1} ^ {\gamma} p _ {k} (x _ {k} \mid x _ {0}, x _ {<   k}), \quad p _ {k} (\nu \mid x _ {0}, x _ {<   k}) = \frac {\exp (U _ {k} (\nu) + B _ {k} (x _ {0} , x _ {<   k} , \nu))}{\sum_ {u \in \mathcal {V}} \exp (U _ {k} (u) + B _ {k} (x _ {0} , x _ {<   k} , u))}. \tag {4}
\]
Here,  \( x_{0} \)  denotes the anchor token from the previous verification cycle,  \( U_{k} \)  is the base logit vector produced by the parallel backbone at position k, and V is the vocabulary. At inference time, the sequential block samples left to right according to  \( p_{k}(\cdot \mid x_{0}, x_{<k}) \) . Because this sampling process is inherently sequential, the block must be computationally lightweight ( \( \tau_{sequential} \ll T_{parallel} \) ) so that the overall draft latency remains dominated by the parallel stage. We describe two instantiations of the sequential block below.
- Markov head. The simplest instantiation restricts \( B_{k} \) to depend only on the immediately preceding token, reducing it to a first-order transition \( B(x_{k-1}, x_{k}) \). In principle this is a full \( V \times V \) matrix \( B \); we approximate it with a low-rank factorization \( B = W_{1}W_{2} \), where \( W_{1} \in \mathbb{R}^{V \times r} \) and \( W_{2} \in \mathbb{R}^{r \times V} \). Given the preceding token \( x_{k-1} \), the transition bias for position \( k \) is:
\[
B (x _ {k - 1}, \cdot) = W _ {1} [ x _ {k - 1} ] W _ {2} \in \mathbb {R} ^ {V}, \tag {5}
\]
where  \( W_{1} \)  serves as an embedding lookup table and  \( W_{2} \)  as a logit projection. The low-rank factorization (r=256 by default) keeps both storage and per-step compute small, making the sequential loop efficient even for large vocabularies. Returning to the earlier example: once position 1 samples “of”, the Markov head boosts “course” and suppresses “problem” at position 2, which mitigates the cross-mode collision.
- RNN head. The Markov head is memoryless beyond one step—position \( k \) cannot access tokens before \( x_{k-1} \). The RNN head relaxes this by maintaining a recurrent state \( s_k \) that accumulates the full prefix history within a block. At each step, the module concatenates the current state \( s_{k-1} \in \mathbb{R}^r \), the previous token embedding \( W_1[x_{k-1}] \in \mathbb{R}^r \), and the backbone hidden \( h_k \in \mathbb{R}^d \) into an input vector \( z_k = [s_{k-1}; W_1[x_{k-1}]; h_k] \in \mathbb{R}^{2r + d} \), then applies a single gated update:
\[
s _ {k} = \sigma (W _ {g} z _ {k}) \odot s _ {k - 1} + \left(1 - \sigma (W _ {g} z _ {k})\right) \odot \tanh (W _ {c} z _ {k}), \tag {6}
\]
\[
B _ {k} (x _ {<   k}, \cdot) = W _ {2} ^ {\top} \tanh (W _ {o} z _ {k}),
\]
where  \( W_{g}, W_{c}, W_{o} \in \mathbb{R}^{(2r+d) \times r} \)  are jointly parameterized by a single linear projection that is split into gate, candidate, and output components. The state  \( s_{0} \)  is initialized to zero.
3.2. Confidence-Scheduled Verification
The semi-autoregressive architecture enables DSpark to generate large draft blocks efficiently. However, producing more draft tokens does not automatically translate to higher end-to-end speedups. Indiscriminately verifying the full draft block can actually degrade overall system throughput, especially in high-concurrency scenarios (Hu et al., 2026; Liu et al., 2024c).
6