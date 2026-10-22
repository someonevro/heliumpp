#ifndef CHROME_BROWSER_UI_VIEWS_FRAME_PRIVACY_TOGGLE_VIEW_H_
#define CHROME_BROWSER_UI_VIEWS_FRAME_PRIVACY_TOGGLE_VIEW_H_

#include <string>

#include "base/memory/raw_ptr.h"
#include "components/prefs/pref_change_registrar.h"
#include "ui/base/metadata/metadata_header_macros.h"
#include "ui/gfx/animation/animation_delegate.h"
#include "ui/gfx/animation/slide_animation.h"
#include "ui/views/view.h"

class Profile;

// Low / Medium / High privacy level switch shown in the sidebar instead of the
// address bar. Reads and writes the same stored mode as the first-run chooser,
// Settings and the new tab page (helium_privacy_mode).
class PrivacyToggleView : public views::View, public gfx::AnimationDelegate {
  METADATA_HEADER(PrivacyToggleView, views::View)

 public:
  explicit PrivacyToggleView(Profile* profile);
  ~PrivacyToggleView() override;

  // Re-reads the stored mode (it may have been changed elsewhere).
  void Refresh();

  // views::View:
  gfx::Size CalculatePreferredSize(
      const views::SizeBounds& available_size) const override;
  void OnPaint(gfx::Canvas* canvas) override;
  bool OnMousePressed(const ui::MouseEvent& event) override;
  bool OnKeyPressed(const ui::KeyEvent& event) override;
  void OnMouseMoved(const ui::MouseEvent& event) override;

  // gfx::AnimationDelegate:
  void AnimationProgressed(const gfx::Animation* animation) override;

 private:
  int IndexAt(int x) const;
  void Select(int index);
  std::u16string Caption() const;

  raw_ptr<Profile> profile_;
  int selected_ = -1;
  int from_ = -1;
  bool restart_required_ = false;
  bool writing_ = false;
  PrefChangeRegistrar pref_registrar_;
  gfx::SlideAnimation slide_{this};
};

#endif  // CHROME_BROWSER_UI_VIEWS_FRAME_PRIVACY_TOGGLE_VIEW_H_
