from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one match in {path}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def patch_candidate_window(path: Path) -> None:
    replace_once(
        path,
        "constexpr int kIndicatorWidthInDefaultDPI = 4;\n",
        "constexpr int kIndicatorWidthInDefaultDPI = 4;\n"
        "constexpr int kModernWindowCornerRadiusInDefaultDPI = 12;\n"
        "constexpr int kModernSelectionCornerRadiusInDefaultDPI = 8;\n"
        "constexpr int kModernSelectionHorizontalInsetInDefaultDPI = 4;\n"
        "constexpr int kModernSelectionVerticalInsetInDefaultDPI = 2;\n",
        "modern UI constants",
    )

    replace_once(
        path,
        "COLORREF ToColorRef(const RendererStyle::RGBAColor& color) {\n"
        "  return RGB(color.r(), color.g(), color.b());\n"
        "}\n",
        "COLORREF ToColorRef(const RendererStyle::RGBAColor& color) {\n"
        "  return RGB(color.r(), color.g(), color.b());\n"
        "}\n\n"
        "int ScaleModernDip(int value, uint32_t dpi) {\n"
        "  return static_cast<int>(value * GetDPIScalingFactor(dpi));\n"
        "}\n\n"
        "void DrawRoundedSurface(HDC dc, const RECT& rect, COLORREF fill_color,\n"
        "                        COLORREF border_color, int radius) {\n"
        "  HBRUSH brush = ::CreateSolidBrush(fill_color);\n"
        "  HPEN pen = ::CreatePen(PS_SOLID, 1, border_color);\n"
        "  if (brush == nullptr || pen == nullptr) {\n"
        "    if (brush != nullptr) ::DeleteObject(brush);\n"
        "    if (pen != nullptr) ::DeleteObject(pen);\n"
        "    FillSolidRect(dc, &rect, fill_color);\n"
        "    return;\n"
        "  }\n"
        "  HGDIOBJ old_brush = ::SelectObject(dc, brush);\n"
        "  HGDIOBJ old_pen = ::SelectObject(dc, pen);\n"
        "  ::RoundRect(dc, rect.left, rect.top, rect.right, rect.bottom, radius,\n"
        "              radius);\n"
        "  ::SelectObject(dc, old_pen);\n"
        "  ::SelectObject(dc, old_brush);\n"
        "  ::DeleteObject(pen);\n"
        "  ::DeleteObject(brush);\n"
        "}\n\n"
        "void DrawRoundedOutline(HDC dc, const RECT& rect, COLORREF border_color,\n"
        "                        int radius) {\n"
        "  HPEN pen = ::CreatePen(PS_SOLID, 1, border_color);\n"
        "  if (pen == nullptr) return;\n"
        "  HGDIOBJ old_pen = ::SelectObject(dc, pen);\n"
        "  HGDIOBJ old_brush = ::SelectObject(dc, ::GetStockObject(NULL_BRUSH));\n"
        "  ::RoundRect(dc, rect.left, rect.top, rect.right, rect.bottom, radius,\n"
        "              radius);\n"
        "  ::SelectObject(dc, old_brush);\n"
        "  ::SelectObject(dc, old_pen);\n"
        "  ::DeleteObject(pen);\n"
        "}\n\n"
        "void ApplyRoundedWindowRegion(HWND hwnd, int width, int height,\n"
        "                              int radius) {\n"
        "  if (hwnd == nullptr || width <= 0 || height <= 0 || radius <= 0) return;\n"
        "  HRGN region = ::CreateRoundRectRgn(0, 0, width + 1, height + 1, radius,\n"
        "                                     radius);\n"
        "  if (region == nullptr) return;\n"
        "  if (::SetWindowRgn(hwnd, region, FALSE) == 0) {\n"
        "    ::DeleteObject(region);\n"
        "  }\n"
        "}\n",
        "modern UI helpers",
    )

    replace_once(
        path,
        "  indicator_width_ = kIndicatorWidthInDefaultDPI * scale_factor;\n",
        "  // Yamatana UI intentionally removes the legacy Mozc footer logo.\n"
        "  footer_logo_.reset();\n"
        "  footer_logo_display_size_ = Size(0, 0);\n\n"
        "  indicator_width_ = kIndicatorWidthInDefaultDPI * scale_factor;\n",
        "remove legacy footer logo",
    )

    replace_once(
        path,
        "  CRect client_rect;\n"
        "  this->GetClientRect(&client_rect);\n\n"
        "  wil::unique_hdc_paint paint_dc;\n",
        "  CRect client_rect;\n"
        "  this->GetClientRect(&client_rect);\n"
        "  ApplyRoundedWindowRegion(\n"
        "      this->m_hWnd, client_rect.Width(), client_rect.Height(),\n"
        "      ScaleModernDip(kModernWindowCornerRadiusInDefaultDPI, dpi_));\n\n"
        "  wil::unique_hdc_paint paint_dc;\n",
        "rounded window region",
    )

    replace_once(
        path,
        "    const CRect selected_rect =\n"
        "        ToCRect(table_layout_->GetRowRect(focused_array_index));\n"
        "    FillSolidRect(dc, &selected_rect,\n"
        "                  ToColorRef(style_.focused_background_color()));\n\n"
        "    ::SetDCBrushColor(dc, ToColorRef(style_.focused_border_color()));\n"
        "    ::FrameRect(dc, &selected_rect,\n"
        "                static_cast<HBRUSH>(::GetStockObject(DC_BRUSH)));\n",
        "    CRect selected_rect =\n"
        "        ToCRect(table_layout_->GetRowRect(focused_array_index));\n"
        "    const int horizontal_inset = ScaleModernDip(\n"
        "        kModernSelectionHorizontalInsetInDefaultDPI, dpi_);\n"
        "    const int vertical_inset = ScaleModernDip(\n"
        "        kModernSelectionVerticalInsetInDefaultDPI, dpi_);\n"
        "    selected_rect.DeflateRect(horizontal_inset, vertical_inset);\n"
        "    if (!selected_rect.IsRectEmpty()) {\n"
        "      DrawRoundedSurface(\n"
        "          dc, selected_rect, ToColorRef(style_.focused_background_color()),\n"
        "          ToColorRef(style_.focused_border_color()),\n"
        "          ScaleModernDip(kModernSelectionCornerRadiusInDefaultDPI, dpi_));\n"
        "    }\n",
        "rounded selected candidate card",
    )

    replace_once(
        path,
        "  // DC brush is available in Windows 2000 and later.\n"
        "  ::SetDCBrushColor(dc, ToColorRef(style_.border_color()));\n"
        "  ::FrameRect(dc, &client_crect,\n"
        "              static_cast<HBRUSH>(::GetStockObject(DC_BRUSH)));\n",
        "  DrawRoundedOutline(\n"
        "      dc, client_crect, ToColorRef(style_.border_color()),\n"
        "      ScaleModernDip(kModernWindowCornerRadiusInDefaultDPI, dpi_));\n",
        "rounded candidate window frame",
    )


def patch_ai_rewriter(path: Path) -> None:
    replace_once(
        path,
        "  for (const auto [current, target] : moves) {\n"
        "    segment->move_candidate(current, target);\n"
        "  }\n"
        "  segment->mutable_candidate(0)->attributes |= converter::Attribute::RERANKED;\n"
        "  return true;\n",
        "  const bool top_changed = !desired.empty() && desired.front() != 0;\n"
        "  for (const auto [current, target] : moves) {\n"
        "    segment->move_candidate(current, target);\n"
        "  }\n"
        "  if (top_changed) {\n"
        "    converter::Candidate* reranked_candidate = segment->mutable_candidate(0);\n"
        "    reranked_candidate->attributes |= converter::Attribute::RERANKED;\n"
        "    // Show the AI badge only when AI actually promotes a different\n"
        "    // Mozc candidate to rank 1. Merely validating Mozc's existing top\n"
        "    // candidate must not make it look AI-selected.\n"
        "    if (reranked_candidate->description.find(\"AI\") == std::string::npos) {\n"
        "      if (!reranked_candidate->description.empty()) {\n"
        "        reranked_candidate->description.append(\"  \");\n"
        "      }\n"
        "      reranked_candidate->description.append(\"AI\");\n"
        "    }\n"
        "  }\n"
        "  return !moves.empty();\n",
        "AI candidate indicator",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply Yamatana AI IME visual patches to a prepared Mozc checkout."
    )
    parser.add_argument(
        "--checkout",
        required=True,
        type=Path,
        help="Root of the prepared Mozc checkout (the directory containing src/).",
    )
    args = parser.parse_args()

    checkout = args.checkout.resolve()
    candidate_window = checkout / "src" / "renderer" / "win32" / "candidate_window.cc"
    ai_rewriter = checkout / "src" / "rewriter" / "ai_rewriter.cc"

    if not candidate_window.is_file():
        raise FileNotFoundError(candidate_window)
    if not ai_rewriter.is_file():
        raise FileNotFoundError(ai_rewriter)

    patch_candidate_window(candidate_window)
    patch_ai_rewriter(ai_rewriter)
    print("MOZC_MODERN_UI_PATCH_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
