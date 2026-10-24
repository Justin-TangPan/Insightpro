export function vendorLogo(vendor: string): string {
  if (/阿里|Alibaba/i.test(vendor)) return "/brand-logos/alibabacloud.svg";
  if (/华为|Huawei/i.test(vendor)) return "/brand-logos/huawei.svg";
  if (/OpenAI/i.test(vendor)) return "/brand-logos/openai.svg";
  if (/Anthropic/i.test(vendor)) return "/brand-logos/anthropic.svg";
  if (/Google/i.test(vendor)) return "/brand-logos/google.svg";
  if (/Meta/i.test(vendor)) return "/brand-logos/meta.svg";
  const domains: [RegExp, string][] = [
    [/Tencent|腾讯/i, "https://cloud.tencent.com/favicon.ico"], [/Volcengine|火山|字节/i, "https://www.volcengine.com/favicon.ico"],
    [/Microsoft|Azure/i, "https://www.microsoft.com/favicon.ico"], [/\bAWS\b|Amazon/i, "https://aws.amazon.com/favicon.ico"],
    [/DeepSeek/i, "https://www.deepseek.com/favicon.ico"], [/\bKimi\b|月之暗面/i, "https://www.kimi.com/favicon.ico"],
    [/MiniMax|稀宇/i, "https://www.minimaxi.com/favicon.ico"], [/\bGLM\b|智谱/i, "https://www.z.ai/favicon.ico"],
  ];
  return domains.find(([pattern]) => pattern.test(vendor))?.[1] || "";
}
export function eventImage(image: string | undefined, vendor: string): string {
  return image?.startsWith("https://") ? image : vendorLogo(vendor);
}
