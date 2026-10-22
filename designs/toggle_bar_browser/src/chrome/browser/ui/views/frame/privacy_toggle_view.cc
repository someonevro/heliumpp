#include "chrome/browser/ui/views/frame/privacy_toggle_view.h"

#include <algorithm>

#include "cc/paint/paint_flags.h"
#include "chrome/browser/helium_privacy_mode/helium_privacy_mode.h"
#include "base/functional/bind.h"
#include "chrome/browser/profiles/profile.h"
#include "components/prefs/pref_service.h"
#include "ui/accessibility/ax_enums.mojom.h"
#include "ui/base/metadata/metadata_impl_macros.h"
#include "ui/color/color_id.h"
#include "ui/color/color_provider.h"
#include "ui/events/event.h"
#include "ui/events/keycodes/keyboard_codes.h"
#include "ui/gfx/canvas.h"
#include "ui/gfx/font_list.h"
#include "ui/gfx/geometry/rect_f.h"
#include "ui/views/accessibility/view_accessibility.h"
#include "ui/views/controls/focus_ring.h"

namespace {

constexpr int kSegmentsHeight = 28;
constexpr int kCaptionGap = 3;
constexpr int kCaptionHeight = 13;
constexpr int kPad = 3;

struct Level {
  const char* id;  // stored mode name
  const char16_t* label;
  const char16_t* tooltip;
  const char16_t* caption;
};

constexpr Level kLevels[] = {
    {"usability", u"Low", u"Low: fewest site problems", u"Fewest site problems"},
    {"medium", u"Medium", u"Medium (Recommended)", u"Recommended"},
    {"maximum", u"High", u"High: strictest, some sites may break",
     u"Strictest, may break sites"},
};
constexpr int kLevelCount = static_cast<int>(std::size(kLevels));

}  // namespace

PrivacyToggleView::PrivacyToggleView(Profile* profile) : profile_(profile) {
  GetViewAccessibility().SetRole(ax::mojom::Role::kRadioGroup);
  GetViewAccessibility().SetName(u"Privacy level");
  SetFocusBehavior(FocusBehavior::ALWAYS);
  views::FocusRing::Install(this);
  slide_.SetSlideDuration(base::Milliseconds(200));
  slide_.SetTweenType(gfx::Tween::EASE_OUT);
  Refresh();
  // Follow changes made elsewhere (homepage switch, Settings, footer menu).
  pref_registrar_.Init(profile_->GetPrefs());
  pref_registrar_.Add("helium.privacy_mode",
                      base::BindRepeating(
                          [](PrivacyToggleView* view) {
                            if (!view->writing_) {
                              view->Refresh();
                            }
                          },
                          base::Unretained(this)));
}

PrivacyToggleView::~PrivacyToggleView() = default;

void PrivacyToggleView::Refresh() {
  const std::string mode = helium_privacy_mode::GetModeName(profile_);
  int index = -1;
  for (int i = 0; i < kLevelCount; ++i) {
    if (mode == kLevels[i].id) {
      index = i;
    }
  }
  selected_ = from_ = index;
  slide_.Reset(1.0);
  SchedulePaint();
}

gfx::Size PrivacyToggleView::CalculatePreferredSize(
    const views::SizeBounds&) const {
  return gfx::Size(150, kSegmentsHeight + kCaptionGap + kCaptionHeight);
}

int PrivacyToggleView::IndexAt(int x) const {
  const int segment_width = std::max(1, width() / kLevelCount);
  return std::clamp(x / segment_width, 0, kLevelCount - 1);
}

void PrivacyToggleView::Select(int index) {
  if (index == selected_ || index < 0 || index >= kLevelCount) {
    return;
  }
  bool restart = false;
  writing_ = true;
  const bool ok =
      helium_privacy_mode::SetMode(profile_, kLevels[index].id, &restart);
  writing_ = false;
  if (!ok) {
    return;
  }
  from_ = selected_ < 0 ? index : selected_;
  selected_ = index;
  restart_required_ = restart;
  slide_.Reset(0.0);
  slide_.Show();
  SchedulePaint();
}

std::u16string PrivacyToggleView::Caption() const {
  if (restart_required_) {
    return u"Restart to fully apply";
  }
  return selected_ >= 0 ? kLevels[selected_].caption : u"Choose a privacy level";
}

void PrivacyToggleView::OnPaint(gfx::Canvas* canvas) {
  const ui::ColorProvider* colors = GetColorProvider();
  const float segment_width = static_cast<float>(width()) / kLevelCount;
  const gfx::RectF track(0, 0, width(), kSegmentsHeight);
  const float radius = kSegmentsHeight / 2.0f;

  cc::PaintFlags flags;
  flags.setAntiAlias(true);
  flags.setStyle(cc::PaintFlags::kFill_Style);
  flags.setColor(colors->GetColor(ui::kColorSysSurface3));
  canvas->DrawRoundRect(track, radius, flags);

  if (selected_ >= 0) {
    const float t = static_cast<float>(slide_.GetCurrentValue());
    const float x = (from_ + (selected_ - from_) * t) * segment_width;
    const gfx::RectF pill(x + kPad, kPad, segment_width - 2 * kPad,
                          kSegmentsHeight - 2 * kPad);
    flags.setColor(colors->GetColor(ui::kColorSysTonalContainer));
    canvas->DrawRoundRect(pill, pill.height() / 2, flags);
  }

  const gfx::FontList font = gfx::FontList().DeriveWithWeight(
      gfx::Font::Weight::MEDIUM);
  for (int i = 0; i < kLevelCount; ++i) {
    const SkColor color = colors->GetColor(i == selected_
                                               ? ui::kColorSysOnTonalContainer
                                               : ui::kColorSysOnSurfaceSubtle);
    canvas->DrawStringRectWithFlags(
        kLevels[i].label, font, color,
        gfx::Rect(static_cast<int>(i * segment_width), 0,
                  static_cast<int>(segment_width), kSegmentsHeight),
        gfx::Canvas::TEXT_ALIGN_CENTER);
  }

  canvas->DrawStringRectWithFlags(
      Caption(), gfx::FontList().DeriveWithSizeDelta(-3),
      colors->GetColor(ui::kColorSysOnSurfaceSubtle),
      gfx::Rect(0, kSegmentsHeight + kCaptionGap, width(), kCaptionHeight),
      gfx::Canvas::TEXT_ALIGN_CENTER);
}

bool PrivacyToggleView::OnMousePressed(const ui::MouseEvent& event) {
  if (!event.IsOnlyLeftMouseButton() || event.y() > kSegmentsHeight) {
    return false;
  }
  Select(IndexAt(event.x()));
  RequestFocus();
  return true;
}

bool PrivacyToggleView::OnKeyPressed(const ui::KeyEvent& event) {
  const int current = selected_ < 0 ? 0 : selected_;
  if (event.key_code() == ui::VKEY_LEFT) {
    Select(std::max(0, current - 1));
    return true;
  }
  if (event.key_code() == ui::VKEY_RIGHT) {
    Select(std::min(kLevelCount - 1, current + 1));
    return true;
  }
  return false;
}

void PrivacyToggleView::OnMouseMoved(const ui::MouseEvent& event) {
  SetTooltipText(event.y() <= kSegmentsHeight
                     ? std::u16string(kLevels[IndexAt(event.x())].tooltip)
                     : std::u16string());
}

void PrivacyToggleView::AnimationProgressed(const gfx::Animation*) {
  SchedulePaint();
}

BEGIN_METADATA(PrivacyToggleView)
END_METADATA
