const logos: [RegExp, string][] = [
  [/阿里|Alibaba/i, "/brand-logos/alibabacloud.svg"],
  [/华为|Huawei/i, "/brand-logos/huawei.svg"],
  [/OpenAI/i, "/brand-logos/openai.svg"],
  [/Anthropic/i, "/brand-logos/anthropic.svg"],
  [/Google/i, "/brand-logos/google.svg"],
  [/Meta/i, "/brand-logos/meta.svg"],
  [/Tencent|腾讯/i, "/brand-logos/tencent-cloud.png"],
  [/Volcengine|火山|字节/i, "/brand-logos/volcengine.png"],
  [/Microsoft|Azure/i, "/brand-logos/microsoft-azure.png"],
  [/\bAWS\b|Amazon/i, "/brand-logos/aws.png"],
  [/DeepSeek/i, "/brand-logos/deepseek.png"],
  [/\bKimi\b|月之暗面/i, "/brand-logos/kimi.png"],
  [/MiniMax|稀宇/i, "/brand-logos/minimax.png"],
  [/\bGLM\b|智谱|Z\.ai/i, "/brand-logos/zai.svg"],
  [/CSDN/i, "/brand-logos/csdn.png"],
  [/知乎|Zhihu/i, "/brand-logos/zhihu.png"],
  [/百度|Baidu/i, "/brand-logos/baidu.png"],
  [/掘金|Juejin/i, "/brand-logos/juejin.png"],
  [/GitHub/i, "/brand-logos/github.png"],
];

export function vendorLogo(vendor: string): string {
  return logos.find(([pattern]) => pattern.test(vendor))?.[1] || "";
}
export function eventImage(image: string | undefined, vendor: string): string {
  return image?.startsWith("https://") ? image : vendorLogo(vendor);
}
