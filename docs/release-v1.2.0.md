## Paired details, preserved evidence

`photo-locate ui` now includes a paired image workspace. Zoom both images, drag them together or independently, draw corresponding regions, and save numbered labels. Click a number to focus the matching regions in both views. Coordinates can also be entered with the keyboard.

HTML/PDF reports now include numbered overviews, paired detail crops and original pixel coordinates. Removed annotations remain in report history; their numbers are never reused. Annotation changes reset the conclusion to candidate for renewed review. Source and reference image files remain unchanged.

The offline demo includes differently framed synthetic images and two saved correspondences. Existing schema-v1 cases remain compatible, with no new model dependency. MIT License continues to apply.

## 双图细节对照，有迹可查

运行 `photo-locate ui`，即可使用新的双图工作区：同步缩放、同步或独立拖动，在两侧分别框选对应细节，命名并保存编号；点击编号同时定位双图。也支持键盘输入原始像素坐标。

HTML／PDF 新增编号总览、局部对照与坐标。误标移除后保留历史，不复用编号；标注变化后需重新审阅结论。原图及参考图文件保持不变。

离线演示采用不同取景范围的虚构图片和两组预置标注。兼容旧 schema-v1 调查，不增加模型依赖，继续采用 MIT License。

## Install / 安装

Download the wheel below, then / 下载下方 wheel 后执行：

```bash
python -m pip install 'photo_location_workflow-1.2.0-py3-none-any.whl[pdf]'
photo-locate ui
```

PDF export requires an embeddable CJK font. `SHA256SUMS.txt` lists download checksums. / PDF 需可嵌入中文字体；校验清单可用于核对下载文件。
