#!/usr/bin/env python3
"""生成纯想风格的 Supabase Auth 验证码邮件。

产物:
    templates/*.html   粘贴到 Supabase Dashboard → Authentication → Email Templates
    auth-config.json   或用 Management API 一次性更新全部模板（见 README）
    assets/header.gif  邮件头图动画：六爻自下而上成卦，朱砂印落款（需 --gif）

用法:
    python supabase/email/build.py
    python supabase/email/build.py --asset-url https://<ref>.supabase.co/storage/v1/object/public/email/header.gif
    pip install pillow && python supabase/email/build.py --gif --seal-font MaShanZheng-Regular.ttf
"""

import argparse
import json
import math
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent

# 头图地址：合并到 main 后即可通过 jsDelivr 访问；国内用户较多时建议换成 Supabase Storage / 阿里云 OSS
DEFAULT_ASSET_URL = (
    "https://cdn.jsdelivr.net/gh/zhangzundaxionghubby-create/"
    "chunxiang-fastapi-temp@main/supabase/email/assets/header.gif"
)
# 与 Dashboard → Authentication → Providers → Email → Email OTP Expiration 保持一致（默认 3600 秒）
OTP_EXPIRY = "1 小时"


# ---------------------------------------------------------------------------
# 邮件文案：key 对应 Supabase 模板名（mailer_templates_<key>_content）
# ---------------------------------------------------------------------------

EMAILS = {
    "magic_link": {
        "subject": "{{ .Token }} 是你的纯想登录验证码",
        "eyebrow": "登录验证",
        "title": "你的登录验证码",
        "intro": "你正在登录纯想，请在登录页面输入下方验证码。",
        "notice": "如果这不是你本人的操作，忽略这封邮件即可，你的账号依然安全。"
        "请勿将验证码告诉任何人，纯想不会以任何方式向你索要验证码。",
    },
    "confirmation": {
        "subject": "{{ .Token }} 是你的纯想注册验证码",
        "eyebrow": "注册验证",
        "title": "欢迎来到纯想",
        "intro": "感谢注册！输入下方验证码，完成邮箱验证。",
        "notice": "如果你没有注册过纯想，忽略这封邮件即可。"
        "请勿将验证码告诉任何人，纯想不会以任何方式向你索要验证码。",
    },
    "reauthentication": {
        "subject": "{{ .Token }} 是你的纯想安全验证码",
        "eyebrow": "安全验证",
        "title": "确认是你本人",
        "intro": "你正在进行一项敏感操作，请输入下方验证码确认身份。",
        "notice": "如果这不是你本人的操作，请尽快检查账号安全。"
        "请勿将验证码告诉任何人，纯想不会以任何方式向你索要验证码。",
    },
}

SANS = ("-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB',"
        "'Microsoft YaHei','Noto Sans SC','Helvetica Neue',Arial,sans-serif")
SERIF = "'Songti SC','STSong','Noto Serif SC','Source Han Serif SC',SimSun,serif"
MONO = "'SF Mono',Menlo,Consolas,'Roboto Mono','Courier New',monospace"

# 表格布局 + 内联样式，兼容 Gmail / Outlook / QQ 邮箱；<style> 只做移动端和深色模式增强
LAYOUT = Template("""\
<!DOCTYPE html>
<html lang="zh-CN" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>$subject</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
<style>
  body { margin:0; padding:0; width:100% !important; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }
  img { border:0; outline:none; text-decoration:none; -ms-interpolation-mode:bicubic; }
  @media (max-width:600px) {
    .cx-outer { padding:24px 10px !important; }
    .cx-pad { padding-left:24px !important; padding-right:24px !important; }
    .cx-title { font-size:22px !important; }
    .cx-code { font-size:32px !important; letter-spacing:8px !important; padding-left:8px !important; }
  }
  @media (prefers-color-scheme:dark) {
    .cx-bg { background:#14110E !important; }
    .cx-card { background:#1E1A16 !important; border-color:#2F2922 !important; }
    .cx-ink { color:#F3ECDF !important; }
    .cx-muted { color:#A3988A !important; }
    .cx-codebox { background:#28221C !important; border-color:#3B332A !important; }
    .cx-rule { border-color:#2F2922 !important; }
  }
  [data-ogsc] .cx-ink { color:#F3ECDF !important; }
  [data-ogsc] .cx-muted { color:#A3988A !important; }
</style>
</head>
<body class="cx-bg" style="margin:0;padding:0;background:#F3EEE4;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">$preheader&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="cx-bg" style="background:#F3EEE4;">
<tr><td align="center" class="cx-outer" style="padding:40px 12px;">
<!--[if mso]><table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;font-family:$sans;">
  <tr><td align="center" class="cx-muted" style="padding:0 0 18px;font-size:12px;line-height:1;letter-spacing:6px;color:#9A8F80;">纯想 · CHUNXIANG</td></tr>
  <tr><td class="cx-card" style="background:#FFFCF7;border:1px solid #E8DFCF;border-radius:20px;overflow:hidden;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td style="font-size:0;line-height:0;"><img src="$asset_url" width="560" alt="纯想 · 六爻成卦" style="display:block;width:100%;max-width:560px;height:auto;border-radius:20px 20px 0 0;"></td></tr>
      <tr><td class="cx-pad" style="padding:36px 44px 0;">
        <p style="margin:0 0 10px;font-size:12px;line-height:1.5;letter-spacing:4px;font-weight:600;color:#BE3422;">$eyebrow</p>
        <h1 class="cx-ink cx-title" style="margin:0 0 12px;font-family:$serif;font-size:26px;line-height:1.35;font-weight:700;color:#26211C;">$title</h1>
        <p class="cx-muted" style="margin:0;font-size:15px;line-height:1.8;color:#6B6156;">$intro</p>
      </td></tr>
      <tr><td class="cx-pad" style="padding:24px 44px 0;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td align="center" class="cx-codebox" style="background:#F6EFE3;border:1px solid #E6D9C3;border-radius:14px;padding:22px 12px;">
            <div class="cx-ink cx-code" style="font-family:$mono;font-size:38px;line-height:1.2;font-weight:700;letter-spacing:12px;padding-left:12px;color:#26211C;-webkit-user-select:all;user-select:all;">{{ .Token }}</div>
          </td>
        </tr></table>
        <p class="cx-muted" style="margin:14px 0 0;text-align:center;font-size:13px;line-height:1.6;color:#9A8F80;">验证码 $expiry内有效，仅可使用一次</p>
      </td></tr>
      <tr><td class="cx-pad" style="padding:28px 44px 36px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td class="cx-rule" style="border-top:1px solid #EEE6D8;font-size:0;line-height:0;">&nbsp;</td></tr></table>
        <p class="cx-muted" style="margin:20px 0 0;font-size:13px;line-height:1.8;color:#8C8174;">$notice</p>
      </td></tr>
    </table>
  </td></tr>
  <tr><td align="center" class="cx-muted" style="padding:24px 12px 0;font-size:12px;line-height:1.8;color:#A0968A;">
    {{ if .Email }}此邮件发送至 {{ .Email }}<br>{{ end }}系统自动发送，请勿直接回复 · <a href="{{ .SiteURL }}" style="color:#BE3422;text-decoration:none;">纯想</a>
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr>
</table>
</body>
</html>
""")


def build_templates(asset_url: str) -> None:
    """渲染全部模板，并生成 Management API 的 PATCH 请求体。"""
    out_dir = HERE / "templates"
    out_dir.mkdir(exist_ok=True)
    config = {}
    for name, copy in EMAILS.items():
        html = LAYOUT.substitute(
            copy,
            preheader=f"{copy['eyebrow']}码 {{{{ .Token }}}}，{OTP_EXPIRY}内有效。",
            expiry=OTP_EXPIRY,
            asset_url=asset_url,
            sans=SANS,
            serif=SERIF,
            mono=MONO,
        )
        (out_dir / f"{name}.html").write_text(html, encoding="utf-8")
        config[f"mailer_subjects_{name}"] = copy["subject"]
        config[f"mailer_templates_{name}_content"] = html
    (HERE / "auth-config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 头图动画（2x 绘制，邮件中按 560×200 显示）
# ---------------------------------------------------------------------------

W, H = 1120, 400
SS = 4  # 超采样倍数，抗锯齿

PAPER = (245, 239, 228)     # 宣纸
INK = (40, 34, 29)          # 墨
CINNABAR = (190, 52, 34)    # 朱砂
ENSO = (234, 224, 206)      # 圆相淡墨

# 泰卦：自下而上 阳阳阳阴阴阴，取"天地交而万物通"之意
HEXAGRAM = (1, 1, 1, 0, 0, 0)
LINE_W, LINE_T, LINE_GAP, YIN_GAP = 260, 26, 22, 40
HEX_X = 364
HEX_H = 6 * LINE_T + 5 * LINE_GAP
HEX_Y = (H - HEX_H) // 2
SEAL_W, SEAL_H = 84, 152
SEAL_X = HEX_X + LINE_W + 48
SEAL_Y = HEX_Y + HEX_H - SEAL_H


def build_gif(path: Path, seal_font: str) -> None:
    from PIL import Image, ImageChops, ImageDraw, ImageFont

    def supersampled(draw_fn, color):
        big = Image.new("RGBA", (W * SS, H * SS), color + (0,))
        draw_fn(ImageDraw.Draw(big), SS)
        return big.resize((W, H), Image.LANCZOS)

    def enso(d, s):
        # 一笔画成的圆相：留一道缺口，收笔渐细
        cx, cy, r = (HEX_X + LINE_W / 2) * s, H / 2 * s, 176 * s
        for i in range(900):
            t = i / 900
            a = math.radians(-70 + 320 * t)
            w = (4 + 7 * math.sin(math.pi * t) ** 0.6) * (1 - 0.7 * t ** 4) * s
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            d.ellipse((x - w, y - w, x + w, y + w), fill=ENSO + (255,))

    def brush(d, x0, y0, x1, y1):
        # 沿笔画铺圆点：起笔略顿、收笔渐提，让爻线有毛笔的轻重
        r0, cy = (y1 - y0) / 2, (y0 + y1) / 2
        steps = int(x1 - x0 - 2 * r0) // 2 or 1
        for k in range(steps + 1):
            u = k / steps
            r = r0 * (1.0 + 0.08 * max(0, 1 - u / 0.12) - 0.16 * u ** 1.5)
            x = x0 + r0 + u * (x1 - x0 - 2 * r0)
            d.ellipse((x - r, cy - r, x + r, cy + r), fill=INK + (255,))

    def line_layer(i, yang):
        # 第 i 爻（自下而上）：阳爻一笔，阴爻中间断开
        y = HEX_Y + (5 - i) * (LINE_T + LINE_GAP)
        half = (LINE_W - YIN_GAP) // 2
        segs = [(HEX_X, HEX_X + LINE_W)] if yang else [
            (HEX_X, HEX_X + half), (HEX_X + LINE_W - half, HEX_X + LINE_W)]

        def draw(d, s):
            for a, b in segs:
                brush(d, a * s, y * s, b * s, (y + LINE_T) * s)

        return supersampled(draw, INK)

    def seal_layer():
        font = ImageFont.truetype(seal_font, 62 * SS)

        def draw(d, s):
            x0, y0, x1, y1 = SEAL_X * s, SEAL_Y * s, (SEAL_X + SEAL_W) * s, (SEAL_Y + SEAL_H) * s
            d.rounded_rectangle((x0, y0, x1, y1), radius=10 * s, fill=CINNABAR + (255,))
            d.rounded_rectangle((x0 + 6 * s, y0 + 6 * s, x1 - 6 * s, y1 - 6 * s),
                                radius=6 * s, outline=PAPER + (255,), width=3 * s)
            for k, ch in enumerate("纯想"):
                d.text(((x0 + x1) / 2, y0 + (y1 - y0) * (0.29 + 0.42 * k)), ch,
                       font=font, fill=PAPER + (255,), anchor="mm")

        center = (SEAL_X + SEAL_W / 2, SEAL_Y + SEAL_H / 2)
        return supersampled(draw, CINNABAR).rotate(3, center=center, resample=Image.BICUBIC), center

    def faded(layer, alpha):
        out = layer.copy()
        out.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        return out

    def revealed(layer, p, soft=36):
        # 自左向右"走笔"，笔锋处柔和过渡
        front = HEX_X - soft + p * (LINE_W + 2 * soft)
        row = bytes(max(0, min(255, int((front - x) / soft * 255))) for x in range(W))
        out = layer.copy()
        out.putalpha(ImageChops.multiply(
            layer.getchannel("A"), Image.frombytes("L", (W, 1), row).resize((W, H))))
        return out

    def stamped(seal, center, scale, alpha):
        cx, cy = center
        big = seal.resize((round(W * scale), round(H * scale)), Image.LANCZOS)
        out = Image.new("RGBA", (W, H), CINNABAR + (0,))
        out.paste(big, (round(cx - cx * scale), round(cy - cy * scale)))
        return faded(out, alpha)

    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    bg.alpha_composite(supersampled(enso, ENSO))
    lines = [line_layer(i, yang) for i, yang in enumerate(HEXAGRAM)]
    seal, seal_center = seal_layer()

    frames, durations = [], []

    def add(progress, ms, line_alpha=1.0, seal_scale=1.0, seal_alpha=0.0):
        img = bg.copy()
        for layer, p in zip(lines, progress):
            if p >= 1:
                img.alpha_composite(faded(layer, line_alpha) if line_alpha < 1 else layer)
            elif p > 0:
                img.alpha_composite(revealed(layer, p))
        if seal_alpha > 0:
            img.alpha_composite(stamped(seal, seal_center, seal_scale, seal_alpha))
        frames.append(img.convert("RGB"))
        durations.append(ms)

    full = [1] * 6
    # 首帧就是完整画面：Outlook 桌面版只显示 GIF 首帧
    add(full, 2600, seal_alpha=1)
    for k in range(1, 6):
        add(full, 60, line_alpha=1 - k / 5, seal_alpha=1 - k / 5)
    add([0] * 6, 300)
    for i in range(6):
        for k in range(1, 7):
            add([1] * i + [1 - (1 - k / 6) ** 3] + [0] * (5 - i), 45)
        durations[-1] += 90
    for scale, alpha in ((1.35, 0.35), (1.15, 0.7), (0.97, 1.0), (1.0, 1.0)):
        add(full, 60, seal_scale=scale, seal_alpha=alpha)

    # 所有帧共用一套由主色两两渐变组成的调色板：走笔、淡出时边缘不会串色
    ramps = ((PAPER, INK, 64), (PAPER, CINNABAR, 48), (ENSO, INK, 32),
             (PAPER, ENSO, 16), (ENSO, CINNABAR, 16))
    colors = [tuple(round(a + (b - a) * k / (n - 1)) for a, b in zip(c0, c1))
              for c0, c1, n in ramps for k in range(n)]
    palette = Image.new("P", (1, 1))
    palette.putpalette([v for c in colors + [PAPER] * (256 - len(colors)) for v in c])
    gif = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    path.parent.mkdir(exist_ok=True)
    gif[0].save(path, save_all=True, append_images=gif[1:], duration=durations, loop=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asset-url", default=DEFAULT_ASSET_URL, help="邮件中头图的公开地址")
    parser.add_argument("--gif", action="store_true", help="重新生成 assets/header.gif（需要 Pillow）")
    parser.add_argument("--seal-font", help="印章字体，推荐 Google Fonts 的 Ma Shan Zheng（OFL 授权）")
    args = parser.parse_args()

    if args.gif:
        if not args.seal_font:
            parser.error("--gif 需要同时指定 --seal-font")
        build_gif(HERE / "assets" / "header.gif", args.seal_font)
    build_templates(args.asset_url)


if __name__ == "__main__":
    main()
