Algorithm 1 Hardware-Aware Prefix Scheduler
Require: Active requests  \( r \in \{1, \ldots, R\} \) ; confidence sequence  \( c_{r,1}, \ldots, c_{r,y} \)  per request; profiled step curve SPS(B)

Ensure: Selected per-request prefix lengths  \( \ell_{1}^{*}, \ldots, \ell_{R}^{*} \) 

1: for r = 1 to R do

2: Compute prefix survival probabilities:  \( a_{r,j} \leftarrow \prod_{i \in j} c_{r,i} \)  for  \( j = 1, \ldots, r \) 

3: end for

4: Construct candidate space  \( \mathcal{E} \leftarrow \{(r, j) \mid a_{r,j} > 0\} \)  and sort descending by  \( a_{r,j} \) 

5: Initialize states:  \( \ell_{r} \leftarrow 0 \)  for all r; Batch size  \( B \leftarrow R \) ; Expected accepts  \( \tau^{*} \leftarrow R \) 

6: Initialize tracking:  \( \Theta_{best} \leftarrow R \cdot SPS(R) \) ; Selected lengths  \( \ell_{r}^{*} \leftarrow 0 \)  for all r

7: for each  \( (r, j) \in \mathcal{E} \)  in sorted order do

8:  \( \ell_{r} \leftarrow j; B \leftarrow B + 1; \tau^{*} \leftarrow \tau^{*} + a_{r,j} \) 

9: Current throughput  \( \Theta \leftarrow \tau^{*} \cdot SPS(B) \) 

10: if  \( \Theta > \Theta_{best} \)  then

11:  \( \Theta_{best} \leftarrow \Theta; Update selected lengths \ell_{r}^{*} \leftarrow \ell_{r} \) 

12: else

13: break

14: end if

15: end for

16: return  \( (\ell_{1}^{*}, \ldots, \ell_{R}^{*}) \)  achieving  \( \Theta_{best} \)
Prior methods (Huang et al., 2024; Li et al., 2024b) typically apply a static threshold to confidence scores to determine verification length. While effective under isolated, single-request assumptions, static thresholds can be suboptimal in high-concurrency production systems, where the utility of verifying a draft token depends heavily on the current system load.
To address this, we formulate verification length selection as a global throughput maximization problem (Algorithm 1). Consider a batch of \( R \) active requests. For request \( r \), let \( c_{r,1},\ldots ,c_{r,r} \) be the per-position confidence estimates, and let \( \ell_r\in \{0,\dots ,r\} \) denote the scheduled verification length. Because speculative decoding dynamically accepts draft tokens only as a continuous prefix, the survival probability of a token at position \( j \) is the cumulative product \( a_{r,j} = \prod_{i\in j}c_{r,i} \).
In a single verification step, the total batch size (measured in tokens) sent to the target model is  \( B = \sum_{r=1}^{R}(1 + \ell_{r}) \) , and the expected number of successfully accepted tokens is  \( \tau = \sum_{r=1}^{R}(1 + \sum_{j=1}^{\ell_{r}} a_{r,j}) \) . Let  \( \text{SPS}(B) \)  denote the engine throughput, measured in steps per second, for a given forward-pass batch size B. Crucially, this capacity curve is profiled once during engine initialization and stored as a lightweight cost table. Our scheduler then aims to maximize the expected system-wide token throughput  \( \Theta = \tau \cdot \text{SPS}(B) \)  by dynamically selecting verification lengths  \( \ell_{1}, \ldots, \ell_{R} \) .
Although finding the global maximum of  \( \Theta \)  appears to be a combinatorial search, the objective structure allows for an efficient greedy solution. Because  \( a_{r,j} \)  is monotonically non-increasing with respect to j (i.e.,  \( a_{r,j} \leq a_{r,j-1} \) ), the marginal gain in expected accepted tokens for extending request r's verification length from j-1 to j is exactly  \( a_{r,j} \) . This monotonicity ensures that sorting candidate tokens globally by  \( a_{r,j} \)  naturally respects intra-block prefix dependencies. Consequently, if the total verification batch size B were fixed, the optimal allocation  \( \{\ell_{r}\} \)  would be determined by greedily selecting the draft tokens with the highest survival probabilities from the global pool of all  \( \{a_{r,j}\} \) .
Building on this insight, the optimization can be evaluated along this greedy admission path.
8