![](images/0.jpg)

图 18: Single-turn and multi-turn violation percentage. Note that these results should be interpreted carefully due to limitations of the prompt set, subjectivity of the review guidelines, content standards, and individual raters.
![](images/1.jpg)

图 19: Violation percentage per risk category. Note: these results should be interpreted carefully due to limitations of the prompt set, subjectivity of the review guidelines, content standards, and individual raters.
rating= 3. As a result, we note that in Figure 17b the average rating of Falcon is much lower than LLAMA 2-CHAT (34B) although their violation percentages look similar (3.88 vs 4.45).
In Figure 18, we report the violation percentage on single- and multi-turn conversations, respectively. A trend across models is that multi-turn conversations are more prone to inducing unsafe responses. That said, LLAMA 2-CHAT still performs well compared to baselines, especially on multi-turn conversations. We also observe that Falcon performs particularly well on single-turn conversations (largely due to its conciseness) but much worse on multi-turn conversations, which could be due to its lack of multi-turn supervised fine-tuning data.
In Figure 19, we show the per-category safety violation percentage of different LLMs. While model performance is similar across categories, LLAMA 2-CHAT has relatively more violations under the unqualified advice category (although still low in an absolute sense), for various reasons, including lack of an appropriate disclaimer (e.g., "I am not a professional") at times. For the other two categories, LLAMA 2-CHAT achieves comparable or lower violation percentage consistently regardless of model sizes.
35