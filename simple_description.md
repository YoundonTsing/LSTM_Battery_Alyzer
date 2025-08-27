项目概述
该项目旨在通过一种混合深度学习模型（CNN-LSTM）来预测锂离子电池的剩余使用寿命（RUL）。它利用电池充电过程中的电压、电流、温度数据以及放电过程中的容量数据作为模型输入。该代码是论文 A Hybrid CNN-LSTM for Battery Remaining Useful Life Prediction with Charging Profiles Data 的实现。
目录结构
RUL_prediction 目录的主要结构和功能如下：
README.md: 项目的说明文档，包含了框架图、模型性能对比、引用信息等。
data/: 存放数据集。
NASA/: 存放 NASA 电池数据集。
charge/: 存放充电数据，分为 train 和 test 子目录。
discharge/: 存放放电数据（主要是容量信息），也分为 train 和 test 子目录。
train/: 包含了模型训练的核心脚本。
MC-SCNN+LSTM.py, SC-CNN+LSTM.py, MC-LSTM.py 等: 对应于 README.md 中提到的不同模型的训练脚本。
utils.py, utils_new.py: 数据预处理和辅助功能的工具脚本（如绘图、加载数据等）。
param_*.py: 存放模型训练所需的超参数（如学习率、批次大小、序列长度等）。
saved/: 用于存放训练好的模型、评估结果和预测图表。
.html 文件: 一些分析报告或项目文档。
.png 文件: README.md 中使用的框架图和结果图。
应用方法
该项目的应用流程（以 MC-SCNN+LSTM.py 为例）如下：
数据准备:
将 NASA 电池数据集解压并放置在 data/NASA/ 目录下。充电数据（电压、电流、温度曲线）和放电数据（容量）需要分别放在 charge 和 discharge 目录中，并划分为 train 和 test 集。
配置参数:
在 train/param_separated.py 文件中配置训练所需的超参数，例如学习率 (lr)、序列长度 (seq_len_lstm, seq_len_cnn)、训练周期 (epochs)、批次大小 (batch_size) 以及保存模型的路径 (save_dir) 等。
模型训练:
直接运行 train/ 目录下的相应训练脚本，例如 python MC-SCNN+LSTM.py。
脚本会自动从 data 目录加载数据。
utils_new.py 中的 extract_VIT_capacity 函数会负责解析原始数据文件，提取出电压(V)、电流(I)、温度(T)序列以及容量(C)数据，并进行归一化处理。
脚本使用 K-Fold 交叉验证来训练和评估模型。
结果产出:
训练完成后，模型权重、评估指标（MAE, MSE, RMSE, MAPE）、预测结果和真实值的对比图表会自动保存到 saved/ 目录下，并为每一次交叉验证的折叠创建一个单独的子目录。
模型架构
MC-SCNN+LSTM 模型是一个多输入的混合模型：
CNN部分: 三个并行的 Conv1D 层分别接收和处理充电过程中的电压、电流和温度序列，以提取空间特征。这些特征被融合（Concatenate）后，再通过一个额外的CNN层进行深化提取。
LSTM部分: 一个独立的 LSTM 层用于处理历史容量序列数据，以捕捉时间序列的依赖性。
融合与输出: CNN 和 LSTM 两个分支提取的特征被拼接在一起，最后通过全连接层（Dense Layer）输出最终的 RUL 预测值。