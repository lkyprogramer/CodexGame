LLAMA 2: Open Foundation and Fine-Tuned Chat Models
Hugo Touvron* Louis Martin† Kevin Stone†
Peter Albert Amjad Almahairi Yasmine Babaei Nikolay Bashlykov Soumya Batra Prajjwal Bhargava Shruti Bhosale Dan Bikel Lukas Blecher Cristian Canton Ferrer Moya Chen Guillem Cucurull David Esibou Jude Fernandes Jeremy Fu Wenyin Fu Brian Fuller Cynthia Gao Vedanuj Goswami Naman Goyal Anthony Hartshorn Saghar Hosseini Rui Hou Hakan Inan Marcin Kardas Viktor Kerkez Madian Khabsa Isabel Kloumann Artem Korenev Punit Singh Koura Marie-Anne Lachaux Thibaut Lavril Jenya Lee Diana Liskovich Yinghai Lu Yuning Mao Xavier Martinet Todor Mihaylov Pushkar Mishra Igor Molybog Yixin Nie Andrew Poulton Jeremy Reizenstein Rashi Rungta Kalyan Saladi Alan Schelten Ruan Silva Eric Michael Smith Ranjan Subramanian Xiaoqing Ellen Tan Binh Tang Ross Taylor Adina Williams Jian Xiang Kuan Puxin Xu Zheng Yan Iliyan Zarov Yuchen Zhang Angela Fan Melanie Kambadur Sharan Narang Aurelien Rodriguez Robert Stojnic Sergey Edunov Thomas Scialom*
GenAI, Meta
Abstract
警告：该PDFifGPT-Academic开源项目调用大语言模型+Latex翻译插件一键生成，版权归原文作者所有。翻译内容可靠性无保障，请仔细鉴别并以原文为准。项目Github地址：https://github.com/binary-husky/gpt_academic/。项目在线体验地址：https://chatpaper.org。当前大语言模型：gpt-3.5-turbo，当前语言模型温度设定：1。为了防止大语言模型的意外谬误产生扩散影响，禁止移除或修改此警告。
在这项工作中，我们开发了并发布了Llama2，这是一组预训练和微调的大规模语言模型（LLMs），其参数范围从70亿到700亿。我们微调的LLMs被称为LLAMA2-CHAT，专为对话使用场景进行了优化。我们的模型在大多数我们测试的基准测试中都优于开源聊天模型，并且基于我们对其有用性和安全性的人工评估，可能是封闭源模型的合适替代品。我们详细描述了我们的微调方法和LLAMA2-CHAT的安全改进，以使社区能够基于我们的工作进行进一步研究，并促进LLM的负责任发展。
*Equal contribution, corresponding authors: {tscialom, htouvron}@meta.com
\( ^{\dagger} \) Second author
Contributions for all the authors can be found in Section A.1.