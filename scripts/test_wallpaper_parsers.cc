// Host-compiled test for the Linux wallpaper config parsers. Run via scripts/test_wallpaper_parsers.sh
#include <cstdio>
#include "chrome/browser/helium_theme/wallpaper_config_parsers.h"
using namespace helium_theme::wallpaper;
static std::string plugin;
static std::string Kde(const std::string& ini, const std::string& activity = "") {
  return ParseKdeAppletsrc(ini, activity, &plugin);
}
static int fails = 0;
#define EXPECT(got, want) do { std::string g = (got), w = (want); if (g != w) { ++fails; \
  std::printf("FAIL line %d: got '%s' want '%s'\n", __LINE__, g.c_str(), w.c_str()); } } while (0)
int main() {
  EXPECT(ParseGSettingsValue("'file:///usr/share/backgrounds/My%20Pic.jpg'\n"), "/usr/share/backgrounds/My Pic.jpg");
  EXPECT(ParseGSettingsValue("'/home/u/a.png'\n"), "/home/u/a.png");
  EXPECT(ParseGSettingsValue("''\n"), "");
  EXPECT(ParseGSettingsValue("'#2c001e'\n"), "");
  EXPECT(ParseGSettingsValue("'http://x/y.jpg'\n"), "");
  EXPECT(ParseGSettingsValue(""), "");

  EXPECT(Kde("[Containments][1][General]\nImage=file:///wrong.jpg\n"
         "[Containments][1][Wallpaper][org.kde.image][General]\nImage=file:///home/u/Pictures/k%20de.jpg\nPreviewImage=x\n"),
         "/home/u/Pictures/k de.jpg");
  EXPECT(Kde("[Containments][1][Wallpaper][org.kde.slideshow][General]\nSlidePaths=/x\n"), "");
  // Leftover group of a deleted desktop (4) before the live one (46); panel 23 has a plugin too.
  const std::string kde =
      "[Containments][23]\nlocation=4\nplugin=org.kde.panel\nwallpaperplugin=org.kde.image\n"
      "[Containments][4][Wallpaper][org.kde.image][General]\nImage=/usr/share/wallpapers/old.png\n"
      "[Containments][46]\nactivityId=a1\nlastScreen=0\nlocation=0\nplugin=org.kde.plasma.folder\nwallpaperplugin=org.kde.image\n"
      "[Containments][46][Wallpaper][org.kde.image][General]\nImage=file:///home/u/live.png\n";
  EXPECT(Kde(kde), "/home/u/live.png");
  EXPECT(plugin, "org.kde.image");
  // Two activities: the current one wins over the first screen of another.
  const std::string two = kde +
      "[Containments][50]\nactivityId=a2\nlastScreen=1\nlocation=0\nwallpaperplugin=org.kde.image\n"
      "[Containments][50][Wallpaper][org.kde.image][General]\nImage=/home/u/a2.png\n";
  EXPECT(Kde(two, "a2"), "/home/u/a2.png");
  EXPECT(Kde(two, "a1"), "/home/u/live.png");
  // Live desktop runs a slideshow: no image, and the caller must not use the default.
  EXPECT(Kde("[Containments][4][Wallpaper][org.kde.image][General]\nImage=/old.png\n"
             "[Containments][7]\nlastScreen=0\nlocation=0\nwallpaperplugin=org.kde.slideshow\n"), "");
  EXPECT(plugin, "org.kde.slideshow");

  EXPECT(ParseXfceDesktopXml("<channel><property name=\"backdrop\"><property name=\"screen0\"><property name=\"monitoreDP-1\">"
         "<property name=\"workspace0\"><property name=\"color-style\" type=\"int\" value=\"0\"/>"
         "<property name=\"last-image\" type=\"string\" value=\"/home/u/a &amp; b.jpg\"/></property>", {}),
         "/home/u/a & b.jpg");
  EXPECT(ParseXfceDesktopXml("<property name=\"last-image\" type=\"empty\"/>", {}), "");
  // An unplugged monitor listed first: the connected one wins, else the first.
  const std::string xfce =
      "<property name=\"monitorHDMI-1\"><property name=\"workspace0\"><property name=\"last-image\" type=\"string\" value=\"/old.jpg\"/></property></property>"
      "<property name=\"monitoreDP-1\"><property name=\"workspace0\"><property name=\"last-image\" type=\"string\" value=\"/live.jpg\"/></property></property>";
  EXPECT(ParseXfceDesktopXml(xfce, {"eDP-1"}), "/live.jpg");
  EXPECT(ParseXfceDesktopXml(xfce, {"DP-2"}), "/old.jpg");

  EXPECT(std::to_string(ParseGnomeAccent("'teal'\n")), std::to_string(0x2190a4));
  EXPECT(std::to_string(ParseGnomeAccent("")), "-1");

  EXPECT(ParseFehbg("#!/bin/sh\nfeh --no-fehbg --bg-fill '/home/u/wall paper.jpg'\n"), "/home/u/wall paper.jpg");
  EXPECT(ParseFehbg("#!/bin/sh\n"), "");

  EXPECT(ParseNitrogen("[xin_-1]\nfile=/home/u/n.jpg\nmode=5\n"), "/home/u/n.jpg");

  EXPECT(ParseSwayConfig("set $mod Mod4\noutput * bg /home/u/sway.png fill\n"), "/home/u/sway.png");
  EXPECT(ParseSwayConfig("output * bg #000000 solid_color\n"), "");
  EXPECT(ParseSwayConfig("# output * bg /commented.png fill\n"), "");

  EXPECT(ParseHyprpaper("preload = /home/u/h.jpg\nwallpaper = DP-1,/home/u/h.jpg\n"), "/home/u/h.jpg");
  EXPECT(ParseHyprpaper("wallpaper = ,~/Pictures/x.png\n"), "~/Pictures/x.png");
  EXPECT(ParseHyprpaper("wallpaper {\n  monitor = DP-1\n  path = /home/u/new.png\n  fit_mode = cover\n}\n"), "/home/u/new.png");
  EXPECT(ParseIniValue("[KDE]\nLookAndFeelPackage=org.kde.breezedark.desktop\n", "KDE", "LookAndFeelPackage"), "org.kde.breezedark.desktop");
  EXPECT(ParseIniValue("[General]\nAccentColor = 61,174,233\n[KDE]\nX=1\n", "General", "AccentColor"), "61,174,233");
  EXPECT(ParseIniValue("[Colors:Window]\nAccentColor=1,2,3\n[General]\n", "General", "AccentColor"), "");
  EXPECT(ParseIniValue("[General]\nAccentColorFromWallpaper=true\n", "General", "AccentColor"), "");
  EXPECT(ParseIniValue("[Wallpaper]\nImage=Next\n", "Wallpaper", "Image"), "Next");
  EXPECT(std::to_string(ParseKdeRgb("61,174,233")), std::to_string(0x3daee9));
  EXPECT(std::to_string(ParseKdeRgb("61,174,233,255")), std::to_string(0x3daee9));
  EXPECT(std::to_string(ParseKdeRgb("61,174")), "-1");
  EXPECT(std::to_string(ParseKdeRgb("300,0,0")), "-1");
  EXPECT(std::to_string(ParseKdeRgb("#3daee9")), "-1");
  if (fails == 0) std::printf("ALL PASS\n");
  return fails != 0;
}
