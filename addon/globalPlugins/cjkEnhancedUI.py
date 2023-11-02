#CJKEnhancedUI.py
#Version 1.5
#Customizations and enhancements by Michael M Chen <nvda.conceptsphere@gmail.com>
#Tested by 蔡宗豪 Victor Cai <surfer0627@gmail.com>
#A global plug-in intended for the CJK locales
#Utilizing the character processing framework, several enhancements are implemented for a more user friendly experience.
#Speech review mode and Braille review mode can be toggled independently with NVDA+0 and NVDA+=(equals) respectively.
#Summary of the speech review mode
#Moving the system or review cursor automatically speaks the first character description for non English characters.
#Pressing numpad2 [or NVDA+.(dot) for laptop] speaks the next character description.
#Pressing Shift+numPad2 or NVDA+Shift+,(comma) for laptop speaks the previous character description.
#Typing into the input composition window automatically speaks the first character description for single characters.
#Summary of the Braille review mode
#There are three modes: "Off", "On", and "Auto".
#Braille review mode off: performs default Braille display behavior.
#Braille review mode on: pressing numpad2 [or nvda+.(dot)] displays the character descriptions.
#Braille review mode auto: moving the system or review cursor within a region  of text automatically displays the character descriptions.
#For "On" and "Auto" mode, typing into the input composition window automatically displays character descriptions for single characters.
#####
# version 1.3
# Upgrading to compatible with NVDA 2019.3 and Python 3 by Tseng Woody <tsengwoody.tw@gmail.com>
#####
# version 1.4
# Upgrading to compatible with NVDA 2020.1 ('getSpeechForSpelling' rename to 'getSpellingSpeech') by Tseng Woody <tsengwoody.tw@gmail.com>
# version 1.5
# Upgrading to compatible with NVDA 2021.1 by Tseng Woody <tsengwoody.tw@gmail.com>
# version 1.6
# Upgrading to compatible with NVDA 2022.1 by Tseng Woody <tsengwoody.tw@gmail.com>
# version 1.7
# Eliminate outdated code and refactor configuration code.
# Upgrading to compatible with NVDA 2023.1 by Tseng Woody <tsengwoody.tw@gmail.com>
# version 1.7.1
# Fixing the initial config bug
# version 1.8
# Upgrading to compatible with NVDA 2023.1 by Tseng Woody <tsengwoody.tw@gmail.com>


import addonHandler
import api
import braille
from braille import BrailleHandler, handler, CONTEXTPRES_CHANGEDCONTEXT, TextInfoRegion
import characterProcessing
import config
from config.configFlags import (
	TetherTo,
)
import controlTypes
import globalPluginHandler
import keyboardHandler
from languageHandler import getLanguage
from logHandler import log
from NVDAObjects.inputComposition import InputComposition, calculateInsertedChars
import queueHandler
from scriptHandler import getLastScriptRepeatCount, script
from speech import getCurrentLanguage, LANGS_WITH_CONJUNCT_CHARS, speech
from speech.commands import *
import synthDriverHandler
import textInfos
import ui

import re
from typing import (
	Optional,
)

addonHandler.initTranslation()

ADDON_SUMMARY = addonHandler.getCodeAddon().manifest["summary"]

config.conf.spec["CJKEnhancedUI"] = {
	"speechReview": "string(default=On)",
	"brailleReview": "string(default=On)",
}

CJK = {}

pattern=re.compile("[a-zA-z]")

def isAlphanumeric(char):
	"""
	Checks whether a character is within the ranges a-z and A-Z (capA and cap Z).
	@param char: a given character
	@type char: string
	@return: whether the character is between a and z
	@rtype: boolean
	"""
	try:
		result = pattern.match(char)
		if result:
			return True
		else:
			return False
	except:
		return False


def custom_getSpellingSpeech(  # noqa: C901
		text: str,
		locale: Optional[str] = None,
		useCharacterDescriptions: bool = False
):
	defaultLanguage=getCurrentLanguage()
	if not locale or (not config.conf['speech']['autoDialectSwitching'] and locale.split('_')[0]==defaultLanguage.split('_')[0]):
		locale=defaultLanguage

	if not text:
		# Translators: This is spoken when NVDA moves to an empty line.
		yield _("blank")
		return
	if not text.isspace():
		text=text.rstrip()

	synth = synthDriverHandler.getSynth()
	synthConfig=config.conf["speech"][synth.name]
	charMode = False
	textLength=len(text)
	count = 0
	localeHasConjuncts = True if locale.split('_',1)[0] in LANGS_WITH_CONJUNCT_CHARS else False
	charDescList = getCharDescListFromText(text,locale) if localeHasConjuncts else text
	for item in charDescList:
		if localeHasConjuncts:
			# item is a tuple containing character and its description
			speakCharAs = item[0]
			charDesc = item[1]
		else:
			charDesc = None
			# item is just a character.
			speakCharAs = item
			if config.conf["CJKEnhancedUI"]["speechReview"] == "Off" and useCharacterDescriptions:
				charDesc=characterProcessing.getCharacterDescription(locale,speakCharAs.lower())
			else:
				#do not speak character descriptions for alphanumeric characters unless the function is called by the review_currentCharacter method.
				#This is to prevent phonetic spelling of the alphabets when typing, and moving the caret and review cursor.
				if isAlphanumeric(speakCharAs) and not CJK["isReviewCharacter"]:
					#The cursor has moved, so reset the previously stored character.
					#This allows  for a more consistent speech feedback by always speaking the phonetic spelling of alphanumeric characters first after the focus moves.
					CJK["previousCharacter"] = ""
				elif config.conf["CJKEnhancedUI"]["speechReview"] == "On":
					#Retrieve the character description one at a time.
					charDesc=speechReview_getCharacterDescription(locale, speakCharAs.lower())

			if charDesc and config.conf["CJKEnhancedUI"]["speechReview"] == "On":
				speakCharAs = "".join(charDesc)
			elif charDesc:
				IDEOGRAPHIC_COMMA = u"\u3001"
				speakCharAs=charDesc[0] if textLength>1 else IDEOGRAPHIC_COMMA.join(charDesc)
			else:
				speakCharAs = characterProcessing.processSpeechSymbol(locale, speakCharAs)

		uppercase=speakCharAs.isupper()
		# if useCharacterDescriptions and charDesc:
			# IDEOGRAPHIC_COMMA = u"\u3001"
			# speakCharAs=charDesc[0] if textLength>1 else IDEOGRAPHIC_COMMA.join(charDesc)
		# else:
			# speakCharAs=characterProcessing.processSpeechSymbol(locale,speakCharAs)'''
		if uppercase and synthConfig["sayCapForCapitals"]:
			# Translators: cap will be spoken before the given letter when it is capitalized.
			speakCharAs=_("cap %s")%speakCharAs
		if uppercase and synth.isSupported("pitch") and synthConfig["capPitchChange"]:
			yield PitchCommand(offset=synthConfig["capPitchChange"])
		if config.conf['speech']['autoLanguageSwitching']:
			yield LangChangeCommand(locale)
		if len(speakCharAs) == 1 and synthConfig["useSpellingFunctionality"]:
			if not charMode:
				yield CharacterModeCommand(True)
				charMode = True
		elif charMode:
			yield CharacterModeCommand(False)
			charMode = False
		if uppercase and  synthConfig["beepForCapitals"]:
			yield BeepCommand(2000, 50)
		yield speakCharAs
		if uppercase and synth.isSupported("pitch") and synthConfig["capPitchChange"]:
			yield PitchCommand()
		yield EndUtteranceCommand()


def customer_handlePendingUpdate(self):
	"""When any region is pending an update, updates the region and the braille display.
	"""
	if not self._regionsPendingUpdate:
		return
	try:
		scrollTo: Optional[TextInfoRegion] = None
		self.mainBuffer.saveWindow()
		for region in self._regionsPendingUpdate:
			from treeInterceptorHandler import TreeInterceptor
			if isinstance(region.obj, TreeInterceptor) and not region.obj.isAlive:
				log.debug("Skipping region update for died tree interceptor")
				continue
			try:
				region.update()
			except Exception:
				log.debugWarning(
					f"Region update failed for {region}, object probably died",
					exc_info=True
				)
				continue
			if isinstance(region, TextInfoRegion) and region.pendingCaretUpdate:
				scrollTo = region
				region.pendingCaretUpdate = False
		self.mainBuffer.update()
		self.mainBuffer.restoreWindow()
		if scrollTo is not None:
			self.scrollToCursorOrSelection(scrollTo)
		if self.buffer is self.mainBuffer:
			self.update()
		elif (
			self.buffer is self.messageBuffer
			and keyboardHandler.keyCounter > self._keyCountForLastMessage
		):
			self._dismissMessage()
	finally:
		self._regionsPendingUpdate.clear()

	region = scrollTo
	if config.conf["CJKEnhancedUI"]["brailleReview"] == "Auto" and CJK["previousRawText"] == region.rawText and CJK["previousCursorPos"] != region.cursorPos:
		#The cursor is inside the raw text of the previous region and its position as moved, so display the character descriptions.
		try:
			i = region.cursorPos
			char = region.rawText[int(_(i or 0))]
			charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char.lower())
			BrailleHandler.message(handler, char+" "+" ".join(charDesc))
		except TypeError:
			BrailleHandler.message(handler, char)
	else:
		#This region has a new raw text, so store the raw text for subsequent comparison.
		CJK["previousRawText"] = region.rawText
	CJK["previousCursorPos"] = region.cursorPos


def custom_reportNewText(self,oldString,newString):
	if (config.conf["keyboard"]["speakTypedCharacters"] or config.conf["keyboard"]["speakTypedWords"]):
		newText=calculateInsertedChars(oldString.strip(u'\u3000'),newString.strip(u'\u3000'))
		newSpeechText = None
		newBrailleText = None
		if config.conf["CJKEnhancedUI"]["speechReview"] == "On" and not isAlphanumeric(newText) and len(newText) == 1:
			try:
				newSpeechText = speechReview_getCharacterDescription(CJK["locale"], newText)
			except TypeError:
				pass
		if (config.conf["CJKEnhancedUI"]["brailleReview"] == "On" or config.conf["CJKEnhancedUI"]["brailleReview"] == "Auto") and not isAlphanumeric(newText) and len(newText) == 1:
			try:
				newBrailleText = newText+" "+" ".join(characterProcessing.getCharacterDescription(CJK["locale"], newText))
			except TypeError:
				pass
		if newSpeechText:
			queueHandler.queueFunction(queueHandler.eventQueue, ui.reviewMessage, newSpeechText)
		elif newText:
			queueHandler.queueFunction(queueHandler.eventQueue,speech.speakText,newText,symbolLevel=characterProcessing.SymbolLevel.ALL)

def speechReview_getCharacterDescription(locale, character):
	"""
	This function is derived from the default getCharacterDescription function specifically to handle the speechreview mode behavior.
	@param locale: the locale (language[_COUNTRY]) the description should be for.
	@type locale: string
	@param character: the character  who's description should be retrieved.
	@type character: string
	@return:  the found description for the given character. if speech/Braille review mode is turned on, one description is returned at a time.
	@rtype: string
	"""
	try:
		l=characterProcessing._charDescLocaleDataMap.fetchLocaleData(locale)
	except LookupError:
		if not locale.startswith('en'):
			return characterProcessing.getCharacterDescription('en',character)
		raise LookupError("en")
	desc=l.getCharacterDescription(character)
	if not desc and not locale.startswith('en'):
		desc=characterProcessing.getCharacterDescription('en',character)

	if config.conf["CJKEnhancedUI"]["speechReview"] == "Off":
	#Perform default behavior.
		return desc
	if not desc:
		#There is no description for the character, so return nothing to allow the character to be passed to the processSymbol function.
		#Allows for speaking of punctuation and symbols absent from the dictionary.
		return None

	#Append the decimal and hexadecimal representation of the character to the description.
	c = ord(character)
	s = "%d," % c+" - ".join(hex(c))
	desc.append(s)
	currentDesc = ""
	if CJK["direction"] != 0 and CJK["previousCharacter"] == character:
		#Determine the list position for the next character description and handle looping between beginning and end of the list.
		CJK["descIndex"] = CJK["descIndex"]+CJK["direction"]
		if abs(CJK["descIndex"]) == len(desc):
			CJK["descIndex"] = 0
	else:
		#The caret or review cursor has moved, so reset the index and store the character for future comparison.
		CJK["previousCharacter"] = character
		CJK["descIndex"] = 0
		if not isAlphanumeric(character):
			#Allow speaking the character alone followed by a pause before the first description.
			#This could be desirable when the user wants to quickly move through a sentence without hearing extra information.
			currentDesc = character
	currentDesc = currentDesc+" "+desc[CJK["descIndex"]]
	#Free the character descriptions from the decimal and hexadecimal representation at the end of the list.
	#This restores default behavior of the characterProcessing.getCharacterDescription function.
	desc.remove(s)
	return currentDesc

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		CJK["locale"] = _(getLanguage())	#Stores the locale of NVDA.
		CJK["previousCharacter"] = ""	#Stores the character which had its description spoken last.
		CJK["direction"] =0	#stores the direction in which the list of descriptions is to be enumerated.
		CJK["descIndex"] = 0	#Stores the list position of the previously spoken character description.
		CJK["isReviewCharacter"] = False	#Stores whether the thread resides in either of the modified reviewCurrentCharacter functions.
		CJK["previousRawText"] = None	#Stores the raw text of the Braille region before the last cursor move.
		CJK["previousCursorPos"] = -1	#Stores the position of the cursor before the last cursor move.

		self.default_getSpellingSpeech = speech.getSpellingSpeech
		self.default_handlePendingUpdate = BrailleHandler._handlePendingUpdate
		self.default_reportNewText = InputComposition.reportNewText

		speech.getSpellingSpeech = custom_getSpellingSpeech
		BrailleHandler._handlePendingUpdate = customer_handlePendingUpdate
		InputComposition.reportNewText = custom_reportNewText

	@script(
		gestures=["kb:nvda+0"],
		description=_("Toggle on or off the CJK enhanced UI speech review mode."),
		category=ADDON_SUMMARY,
	)
	def script_ToggleSpeechReview(self,gesture):
		if config.conf["CJKEnhancedUI"]["speechReview"] == "Off":
			config.conf["CJKEnhancedUI"]["speechReview"] = "On"
		else:
			config.conf["CJKEnhancedUI"]["speechReview"] = "Off"
		ui.message(_("Speech review mode %s")%config.conf["CJKEnhancedUI"]["speechReview"])

	@script(
		gestures=["kb:nvda+="],
		description=_("Toggle the Braille review mode between Review, Auto, and Off."),
		category=ADDON_SUMMARY,
	)
	def script_ToggleBrailleReview(self,gesture):
		if config.conf["CJKEnhancedUI"]["brailleReview"] == "Off":
			config.conf["CJKEnhancedUI"]["brailleReview"] = "On"
		elif config.conf["CJKEnhancedUI"]["brailleReview"] == "On":
			config.conf["CJKEnhancedUI"]["brailleReview"] = "Auto"
		else:
			config.conf["CJKEnhancedUI"]["brailleReview"] = "Off"
		ui.message(_("Braille review mode %s")%config.conf["CJKEnhancedUI"]["brailleReview"])

	@script(
		gestures=["kb:numPad1", "kb(laptop):nvda+leftarrow"],
		description=_("Moves the review cursor to the previous character of the current navigator object and speaks it"),
		category=ADDON_SUMMARY,
	)
	def script_modified_reviewPreviousCharacter(self,gesture):
		#Add character description Braille output to the review character when Braille review mode is set to "Auto".
		lineInfo=api.getReviewPosition().copy()
		lineInfo.expand(textInfos.UNIT_LINE)
		charInfo=api.getReviewPosition().copy()
		charInfo.expand(textInfos.UNIT_CHARACTER)
		charInfo.collapse()
		res=charInfo.move(textInfos.UNIT_CHARACTER,-1)
		if res==0 or charInfo.compareEndPoints(lineInfo,"startToStart")<0:
			ui.reviewMessage(_("Left"))
			reviewInfo=api.getReviewPosition().copy()
			reviewInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(reviewInfo, unit=textInfos.UNIT_CHARACTER, reason=controlTypes.OutputReason.CARET)
			char = reviewInfo.text.lower()
			if not isAlphanumeric(char) and config.conf["CJKEnhancedUI"]["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
		else:
			api.setReviewPosition(charInfo)
			charInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(charInfo, unit=textInfos.UNIT_CHARACTER, reason=controlTypes.OutputReason.CARET)
			char = charInfo.text.lower()
			if not isAlphanumeric(char) and config.conf["CJKEnhancedUI"]["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass

	@script(
		gestures=["kb:numPad3", "kb(laptop):nvda+rightarrow"],
		description=_("Moves the review cursor to the next character of the current navigator object and speaks it"),
		category=ADDON_SUMMARY,
	)
	def script_modified_review_nextCharacter(self,gesture):
		#Add character description Braille output to the review character when Braille review mode is turned on.
		lineInfo=api.getReviewPosition().copy()
		lineInfo.expand(textInfos.UNIT_LINE)
		charInfo=api.getReviewPosition().copy()
		charInfo.expand(textInfos.UNIT_CHARACTER)
		charInfo.collapse()
		res=charInfo.move(textInfos.UNIT_CHARACTER,1)
		if res==0 or charInfo.compareEndPoints(lineInfo,"endToEnd")>=0:
			ui.reviewMessage(_("Right"))
			reviewInfo=api.getReviewPosition().copy()
			reviewInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(reviewInfo, unit=textInfos.UNIT_CHARACTER, reason=controlTypes.OutputReason.CARET)
			char = reviewInfo.text.lower()
			if not isAlphanumeric(char) and config.conf["CJKEnhancedUI"]["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
		else:
			api.setReviewPosition(charInfo)
			charInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(charInfo, unit=textInfos.UNIT_CHARACTER, reason=controlTypes.OutputReason.CARET)
			char = charInfo.text.lower()
			if not isAlphanumeric(char) and config.conf["CJKEnhancedUI"]["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass

	@script(
		gestures=["kb:numPad2", "kb(laptop):NVDA+."],
		description=_("Enumerates in forward order through the list of character descriptions in the dictionary."),
		category=ADDON_SUMMARY,
	)
	def script_forward_review_currentCharacter(self,gesture):
		#When speech review mode is enabled, the first character description is spoken on first script call.
		#When Braille review mode is set to "On" or "Auto", character descriptions are displayed on the first script call.
		CJK["direction"]=1
		info=api.getReviewPosition().copy()
		info.expand(textInfos.UNIT_CHARACTER)
		count = getLastScriptRepeatCount()

		try:
			c = ord(info.text)
		except:
			c=0

		if count == 1 or (config.conf["CJKEnhancedUI"]["speechReview"] == "On" or config.conf["CJKEnhancedUI"]["brailleReview"] != "Off"):
			CJK["isReviewCharacter"] = True
			if count == 1 or config.conf["CJKEnhancedUI"]["speechReview"] == "On":
				speech.speakSpelling(info.text,useCharacterDescriptions=True)
			else:
				speech.speakTextInfo(info, unit=textInfos.UNIT_CHARACTER, reason=controlTypes.OutputReason.CARET)
			if config.conf["CJKEnhancedUI"]["brailleReview"] == "On" or config.conf["CJKEnhancedUI"]["brailleReview"] == "Auto":
				try:
					char = info.text.lower()
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
		elif count == 0:
			speech.speakTextInfo(info, unit=textInfos.UNIT_CHARACTER, reason=controlTypes.OutputReason.CARET)
		else:
			try:
				speech.speakMessage("%d," % c)
				speech.speakSpelling(hex(c))
			except:
				speech.speakTextInfo(info, unit=textInfos.UNIT_CHARACTER, reason=controlTypes.OutputReason.CARET)
		#Reset parameters to prepare for the next call.
		CJK["direction"] = 0
		CJK["isReviewCharacter"] = False

	@script(
		gestures=["kb:Shift+numPad2", "kb(laptop):NVDA+Shift+."],
		description=_("Enumerates in reverse order through the list of character descriptions in the dictionary."),
		category=ADDON_SUMMARY,
	)
	def script_reverse_review_currentCharacter(self,gesture):
		CJK["direction"] = -1
		CJK["isReviewCharacter"] = True
		info=api.getReviewPosition().copy()
		info.expand(textInfos.UNIT_CHARACTER)
		speech.speakSpelling(info.text,useCharacterDescriptions=True)
		CJK["direction"] = 0
		CJK["isReviewCharacter"] = False

	def terminate(self):
		speech.getSpellingSpeech = self.default_getSpellingSpeech
		BrailleHandler._doCursorMove = self.default_doCursorMove
		InputComposition.reportNewText = self.default_reportNewText
		super().terminate()
