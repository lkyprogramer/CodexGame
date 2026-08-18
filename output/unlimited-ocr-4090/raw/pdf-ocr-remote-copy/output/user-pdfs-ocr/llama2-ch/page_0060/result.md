
图 25: Distribution of human preference data rating over batches. Over time, the share of samples with an unsure or negligibly better rating become larger with better performing LLAMA 2-CHAT trained and available for preference data annotation.
iterative model update and preference data annotation procedure - with better-performing LLAMA 2-CHAT models used for response sampling over time, it becomes challenging for annotators to select a better one from two equally high-quality responses.
A.3.2 Curriculum Strategy for Meta Human Preference Data
High quality data is critical for alignment as discussed for SFT. We worked closely with the annotation platforms during our fine-tuning process, and opted for a curriculum annotation strategy. With the first model, the annotators were asked to make prompts relatively simple, and then to progressively move towards

Figure 26: Annotation curriculum. Evolution for each new batch of the maximum and median score given a reward model for prompts samples with a models trained on each of the batches. We can see that the score progressively decrease, suggesting that the prompts are on average harder in the most recent batches.
60