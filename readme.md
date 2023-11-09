# CJKEnhancedUI

Customizations and enhancements by Michael M Chen <nvda.conceptsphere@gmail.com>

Tested by 蔡宗豪 Victor Cai <surfer0627@gmail.com>

Maintained by Tseng Woody <tsengwoody.tw@gmail.com> (from version 1.2.1).

A global plug-in intended for the CJK locales

Utilizing the character processing framework, several enhancements are implemented for a more user friendly experience.

Speech review mode and Braille review mode can be toggled independently with NVDA+0 and NVDA+=(equals) respectively.

## Summary of the speech review mode

Moving the system or review cursor automatically speaks the first character description for non English characters.

Pressing numpad2 [or NVDA+.(dot) for laptop] speaks the next character description.

Pressing Shift+numPad2 or NVDA+Shift+,(comma) for laptop speaks the previous character description.

Typing into the input composition window automatically speaks the first character description for single characters.

## Summary of the Braille review mode

There are three modes: "Off", "On", and "Auto".

*	Braille review mode off: performs default Braille display behavior.
*	Braille review mode on: pressing numpad2 [or nvda+.(dot)] displays the character descriptions.
*	Braille review mode auto: moving the system or review cursor within a region  of text automatically displays the character descriptions.

For "On" and "Auto" mode, typing into the input composition window automatically displays character descriptions for single characters.

## update log

v1.2.1: Fix bug(Pressing numPad2 can't speak current character) by Tseng Woody.

v1.3: Upgrading to compatible with NVDA 2019.3 and Python 3 by Tseng Woody.

v 1.8

1. Compatible with NVDA 2023.3
2. Fixed an issue where, when speech review mode/braille review mode is off, it does not revert to NVDA's original behavior, such as pressing numpad2 three times not announcing the unicode encoding.
3. Adjusted the names for speech review/braille review toggle.

1. 相容性更新至 NVDA 2023.3
2. 修正語音檢視模式/點字檢視模式 off 時，不是 NVDA 原本的行為，例如按 3 下 numpad2 語音/點字不會讀出 unicode 編碼	
3. 語音檢視/點字檢視開關名稱調整
