import {
  Building2, Factory, Stethoscope, ShoppingCart,
  Landmark, Globe, GraduationCap, Truck, Zap, Leaf,
} from "lucide-react";

export const industryIcons: Record<string, React.ElementType> = {
  "政务": Building2, "制造": Factory, "医疗": Stethoscope,
  "金融": Landmark, "零售": ShoppingCart, "教育": GraduationCap,
  "交通": Truck, "能源": Zap, "农业": Leaf, "通用": Globe,
};

// 瑞士式纯色 tile（黑 / 安全橙轮换，白图标可见）
export const industryColors: Record<string, string> = {
  "政务": "bg-ink",
  "制造": "bg-signal",
  "医疗": "bg-ink",
  "金融": "bg-signal",
  "零售": "bg-signal",
  "教育": "bg-ink",
  "交通": "bg-signal",
  "能源": "bg-ink",
  "农业": "bg-signal",
  "通用": "bg-ink",
};
