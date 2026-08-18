<table><tr><td></td><td>Avg</td><td>Safe Chosen Unsafe Rejected</td><td>Safe Chosen Safe Rejected</td><td>Unsafe Chosen Unsafe Rejected</td><td>Unsafe Response Recall</td></tr><tr><td>Baseline</td><td>63.7</td><td>93.0</td><td>56.0</td><td>59.5</td><td>73.0</td></tr><tr><td>+ Auxiliary Safety Loss</td><td>64.5</td><td>94.3</td><td>56.9</td><td>59.9</td><td>90.4</td></tr></table>
as 29: Ablation on safety auxiliary loss term for safety reward modeling. The safety auxiliary loss boosts accuracy on all 3 categories as well as the recall of unsafe response, measured by the percentage of unsafe responses captured with a reward score threshold of 0.5 (i.e., negative values before Sigmoid).
<table><tr><td>Dialogue Turn</td><td>Baseline</td><td>+GAtt</td></tr><tr><td>2</td><td>100%</td><td>100%</td></tr><tr><td>4</td><td>10%</td><td>100%</td></tr><tr><td>6</td><td>0%</td><td>100%</td></tr><tr><td>20</td><td>0%</td><td>100%</td></tr></table>
as 30: GAtt results. LLAMA 2-CHAT with GAtt is able to refer to attributes 100% of the time, for up to 20 turns from our human evaluation. We limited the evaluated attributes to public figures and hobbies.
The attention now spans beyond 20 turns. We tested the model ability to remember the system arguments trough a human evaluation. The arguments (e.g. hobbies, persona) are defined during the first message, and then from turn 2 to 20. We explicitly asked the model to refer to them (e.g. "What is your favorite hobby?", "What is your name?"), to measure the multi-turn memory ability of LLAMA 2-CHAT. We report the results in Table 30. Equipped with GAtt, LLAMA 2-CHAT maintains 100% accuracy, always referring to the defined attribute, and so, up to 20 turns (we did not extend the human evaluation more, and all the examples had less than 4048 tokens in total over the turns). As a comparison, LLAMA 2-CHAT without GAtt can not anymore refer to the attributes after only few turns: from 100% at turn t+1, to 10% at turn t+3 and then 0%.
![](images/0.jpg)

![](images/1.jpg)

![](images/2.jpg)

图 27: Reward model score distribution shift caused by incorporating preference rating based margin in ranking loss. With the margin term, we observe a binary split pattern in reward distribution, especially with a larger margin.
62