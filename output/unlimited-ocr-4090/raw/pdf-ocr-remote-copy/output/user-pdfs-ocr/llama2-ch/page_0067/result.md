![](images/0.jpg)

![](images/1.jpg)

图 31: Win rate of LLAMA 2-CHAT versus ChatGPT analyzed by number of turns (Left) in the prompt and word count (Right) for the prompt and generation combined. For the word count plot, we report the win rate for each quintile. The maximum total word count (prompt and generation) is 2432. We do not see any trends in win rate with either word count or turn count.
the hallucination rate of either model. In 31, we also share the win rate by number of turns and total word count for prompts and generation. We do not see any trends in win rate in either case.
A.4 Additional Details for Safety
A.4.1 Tension between Safety and Helpfulness in Reward Modeling
We briefly discussed the tension between safety and helpfulness in Section 3.2.2 and how it leads to optimizing two separate reward models for helpfulness and safety in our study. Here we show more evidence and qualitative results to manifest this tension. Figure 32 are two scatter plots of helpfulness and safety reward model scores on the safety test set for safe and unsafe responses. The tension can be observed at the bottom right corner (i.e., high safety score but low helpfulness score) in the safe response plot (left) and the top left corner (i.e., low safety score but high helpfulness score) in the unsafe response plot (right). We also list two qualitative examples where safety and helpfulness reward models don't agree with each other in Table 35.
A.4.2 Qualitative Results on Safety Data Scaling
In Section 4.2.3, we study the impact of adding more safety data into model RLHF in a quantitative manner. Here we showcase a few samples to qualitatively examine the evolution of model behavior when we scale safety data in Tables 36, 37, and 38. In general, we are observing that LLAMA 2-CHAT becomes safer responding to unsafe prompts with more safety data used. For example, LLAMA 2-CHAT learns to refuse to generate offensive content (Table 36) once we use \(50\%\) of safety data. In the meantime, we also observe that LLAMA 2-CHAT starts to be behave more conservatively when there are offensive (e.g., abomination in Table 37) or sensitive words (e.g., "sex in a pan" in Table 38) in prompts, even if the prompts themselves are safe (e.g., sex in a pan is the name of a dessert).
A.4.3 English Pronouns
The terms that we use for the pronoun analyses are consistent with the PaLM 2 paper (Anil et al., 2023):
67