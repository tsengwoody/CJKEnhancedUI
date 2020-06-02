#CJKEnhancedUI.py
#Version 1.4
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
# version 1.4
# Upgrading to compatible with NVDA 2019.3 and Python 3 by Tseng Woody <tsengwoody.tw@gmail.com>
#####
# version 1.4
# Upgrading to compatible with NVDA 2020.1 ('getSpeechForSpelling' rename to 'getSpellingSpeech') by Tseng Woody <tsengwoody.tw@gmail.com>


import braille
from braille import BrailleHandler, handler
import characterProcessing
import config
from config import conf
from globalCommands import SCRCAT_TEXTREVIEW
import globalPluginHandler
import keyboardHandler
from languageHandler import getLanguage
from NVDAObjects.inputComposition import InputComposition, calculateInsertedChars
import scriptHandler
import speech
from speech import *
import ui
import queueHandler
import controlTypes

#Check the config file for existing version of the plug-in.
try:
	if conf["CJKEnhancedUI"]["version"] == "1.2":
		#The config section is up to date, so continue initializing the plug-in.
		pass
	else:
		#Maintain the config section from the previous version.
		#the CJK["isAlphanumeric"] variable is deprecated, so reset the config section to remove it.
		speechReview = conf["CJKEnhancedUI"]["speechReview"]
		brailleReview = conf["CJKEnhancedUI"]["brailleReview"]
		conf["CJKEnhancedUI"] = {}
		conf["CJKEnhancedUI"]["version"] = "1.2"
		conf["CJKEnhancedUI"]["speechReview"] = speechReview
		conf["CJKEnhancedUI"]["brailleReview"] = brailleReview
except KeyError:
	#Either this is a fresh install, or the config section is for an older version.
#Initialize the config section.
	conf["CJKEnhancedUI"] = {}
	conf["CJKEnhancedUI"]["version"] = "1.2"
	conf["CJKEnhancedUI"]["speechReview"] = "On"	#The speech review mode is turned on by default.
	conf["CJKEnhancedUI"]["brailleReview"] = "On"	#The Braille review mode is set to "On" by default.

CJK = conf["CJKEnhancedUI"]

def isAlphanumeric(char):
	"""
	Checks whether a character is within the ranges a-z and A-Z (capA and cap Z).
	@param char: a given character
	@type char: string
	@return: whether the character is between a and z
	@rtype: boolean
	"""
	try:
		c = ord(char)
	except:
		c = 0
	if (c >= ord("a") and c <= ord("z")) or (c >= ord("A") and c <= ord("Z")):
		return True
	else:
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

	synth = getSynth()
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
			if CJK["speechReview"] == "Off" and useCharacterDescriptions:
				charDesc=characterProcessing.getCharacterDescription(locale,speakCharAs.lower())
			else:
				#do not speak character descriptions for alphanumeric characters unless the function is called by the review_currentCharacter method.
				#This is to prevent phonetic spelling of the alphabets when typing, and moving the caret and review cursor.
				if isAlphanumeric(speakCharAs) and not CJK["isReviewCharacter"]:
					#The cursor has moved, so reset the previously stored character.
					#This allows  for a more consistent speech feedback by always speaking the phonetic spelling of alphanumeric characters first after the focus moves.
					CJK["previousCharacter"] = ""
				elif CJK["speechReview"] == "On":
					#Retrieve the character description one at a time.
					charDesc=speechReview_getCharacterDescription(locale, speakCharAs.lower())

			if charDesc and CJK["speechReview"] == "On":
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


def custom_doCursorMove(self, region):
	"""
	This is derived from BrailleHandler._doCursorMove to handle the Braille review behavior.
	When the cursor is moved to a new raw text region, the region is displayed in Braille.
	Once the cursor is moved with left and right arrow, the character descriptions  are displayed for each character at the cursor position.
	@param self: the instance of BrailleHandler currently initialized
	@type self: braille.BrailleHandler
	@param region: the region of Braille displayed
	@type region: braille.Region
	"""
	self.mainBuffer.saveWindow()
	region.update()
	self.mainBuffer.update()
	self.mainBuffer.restoreWindow()
	if region.brailleCursorPos is not None:
		self.mainBuffer.scrollTo(region, region.brailleCursorPos)
	if self.buffer is self.mainBuffer:
		self.update()
	elif self.buffer is self.messageBuffer and keyboardHandler.keyCounter>self._keyCountForLastMessage:
		self._dismissMessage()

	if CJK["brailleReview"] == "Auto" and CJK["previousRawText"] == region.rawText and CJK["previousCursorPos"] != region.cursorPos:
		#The cursor is inside the raw text of the previous region and its position as moved, so display the character descriptions.
		try:
			i = region.cursorPos
			char = region.rawText[int(_(i or 0))]
			charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char.lower())
			#speech.speakMessage("braille output: "+char+" "+" ".join(charDesc))
			BrailleHandler.message(handler, char+" "+" ".join(charDesc))
		except TypeError:
			#speech.speakMessage("braille output: "+char)
			BrailleHandler.message(handler, char)
	else:
		#This region has a new raw text, so store the raw text for subsequent comparison.
		CJK["previousRawText"] = region.rawText
		#speech.speakMessage("raw text "+region.rawText)
	CJK["previousCursorPos"] = region.cursorPos

def custom_reportNewText(self,oldString,newString):
	if (config.conf["keyboard"]["speakTypedCharacters"] or config.conf["keyboard"]["speakTypedWords"]):
		newText=calculateInsertedChars(oldString.strip(u'\u3000'),newString.strip(u'\u3000'))
		newSpeechText = None
		newBrailleText = None
		if CJK["speechReview"] == "On" and not isAlphanumeric(newText) and len(newText) == 1:
			try:
				newSpeechText = speechReview_getCharacterDescription(CJK["locale"], newText)
			except TypeError:
				pass
		if (CJK["brailleReview"] == "On" or CJK["brailleReview"] == "Auto") and not isAlphanumeric(newText) and len(newText) == 1:
			try:
				newBrailleText = newText+" "+" ".join(characterProcessing.getCharacterDescription(CJK["locale"], newText))
			except TypeError:
				pass
		if newSpeechText:
			queueHandler.queueFunction(queueHandler.eventQueue,speech.speakMessage,newSpeechText)
		elif newText:
			queueHandler.queueFunction(queueHandler.eventQueue,speech.speakText,newText,symbolLevel=characterProcessing.SYMLVL_ALL)
		#if newBrailleText:
			#queueHandler.queueFunction(queueHandler.eventQueue, speech.speakMessage, "braille output "+newBrailleText)
			#queueHandler.queueFunction(queueHandler.eventQueue, BrailleHandler.message, handler, newBrailleText)
		#elif (CJK["brailleReview"] == "On" or CJK["brailleReview"] == "Auto") and newText:
			#queueHandler.queueFunction(queueHandler.eventQueue, speech.speakMessage, "braille output "+newText)
			#queueHandler.queueFunction(queueHandler.eventQueue, BrailleHandler.message, handler, newText)

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

	if CJK["speechReview"] == "Off":
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
		super(GlobalPlugin, self).__init__()
		CJK["locale"] = _(getLanguage())	#Stores the locale of NVDA.
		CJK["previousCharacter"] = ""	#Stores the character which had its description spoken last.
		CJK["direction"] =0	#stores the direction in which the list of descriptions is to be enumerated.
		CJK["descIndex"] = 0	#Stores the list position of the previously spoken character description.
		CJK["isReviewCharacter"] = False	#Stores whether the thread resides in either of the modified reviewCurrentCharacter functions.
		CJK["previousRawText"] = None	#Stores the raw text of the Braille region before the last cursor move.
		CJK["previousCursorPos"] = -1	#Stores the position of the cursor before the last cursor move.

		self.default_getSpeechForSpelling = speech.getSpeechForSpelling
		self.default_doCursorMove = BrailleHandler._doCursorMove
		self.default_reportNewText = InputComposition.reportNewText

		speech.getSpellingSpeech = custom_getSpellingSpeech
		BrailleHandler._doCursorMove = custom_doCursorMove
		InputComposition.reportNewText = custom_reportNewText

	def script_ToggleSpeechReview(self,gesture):
		if CJK["speechReview"] == "Off":
			CJK["speechReview"] = "On"
		else:
			CJK["speechReview"] = "Off"
		ui.message(_("Speech review mode "+CJK["speechReview"]))
	script_ToggleSpeechReview.__doc__=_("Toggle on or off the CJK enhanced UI speech review mode.")

	def script_ToggleBrailleReview(self,gesture):
		if CJK["brailleReview"] == "Off":
			CJK["brailleReview"] = "On"
		elif CJK["brailleReview"] == "On":
			CJK["brailleReview"] = "Auto"
		else:
			CJK["brailleReview"] = "Off"
		ui.message(_("Braille review mode "+CJK["brailleReview"]))
	script_ToggleBrailleReview.__doc__=_("Toggle the Braille review mode between Review, Auto, and Off.")

	def script_modified_reviewPreviousCharacter(self,gesture):
		#Add character description Braille output to the review character when Braille review mode is set to "Auto".
		lineInfo=api.getReviewPosition().copy()
		lineInfo.expand(textInfos.UNIT_LINE)
		charInfo=api.getReviewPosition().copy()
		charInfo.expand(textInfos.UNIT_CHARACTER)
		charInfo.collapse()
		res=charInfo.move(textInfos.UNIT_CHARACTER,-1)
		if res==0 or charInfo.compareEndPoints(lineInfo,"startToStart")<0:
			speech.speakMessage(_("left"))
			reviewInfo=api.getReviewPosition().copy()
			reviewInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(reviewInfo,unit=textInfos.UNIT_CHARACTER,reason=controlTypes.REASON_CARET)
			char = reviewInfo.text.lower()
			if not isAlphanumeric(char) and CJK["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					#speech.speakMessage("braille output: "+char+" "+" ".join(charDesc))
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
		else:
			api.setReviewPosition(charInfo)
			charInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(charInfo,unit=textInfos.UNIT_CHARACTER,reason=controlTypes.REASON_CARET)
			char = charInfo.text.lower()
			if not isAlphanumeric(char) and CJK["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					#speech.speakMessage("braille output: "+char+" "+" ".join(charDesc))
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
	# Translators: Input help mode message for move review cursor to previous character command.
	script_modified_reviewPreviousCharacter.__doc__=_("Moves the review cursor to the previous character of the current navigator object and speaks it")
	script_modified_reviewPreviousCharacter.category=SCRCAT_TEXTREVIEW

	def script_modified_review_nextCharacter(self,gesture):
		#Add character description Braille output to the review character when Braille review mode is turned on.
		lineInfo=api.getReviewPosition().copy()
		lineInfo.expand(textInfos.UNIT_LINE)
		charInfo=api.getReviewPosition().copy()
		charInfo.expand(textInfos.UNIT_CHARACTER)
		charInfo.collapse()
		res=charInfo.move(textInfos.UNIT_CHARACTER,1)
		if res==0 or charInfo.compareEndPoints(lineInfo,"endToEnd")>=0:
			speech.speakMessage(_("right"))
			reviewInfo=api.getReviewPosition().copy()
			reviewInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(reviewInfo,unit=textInfos.UNIT_CHARACTER,reason=controlTypes.REASON_CARET)
			char = reviewInfo.text.lower()
			if not isAlphanumeric(char) and CJK["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					#speech.speakMessage("braille output: "+char+" "+" ".join(charDesc))
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
		else:
			api.setReviewPosition(charInfo)
			charInfo.expand(textInfos.UNIT_CHARACTER)
			speech.speakTextInfo(charInfo,unit=textInfos.UNIT_CHARACTER,reason=controlTypes.REASON_CARET)
			char = charInfo.text.lower()
			if not isAlphanumeric(char) and CJK["brailleReview"] == "Auto":
				try:
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					#speech.speakMessage("braille output: "+char+" "+" ".join(charDesc))
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
	# Translators: Input help mode message for move review cursor to next character command.
	script_modified_review_nextCharacter.__doc__=_("Moves the review cursor to the next character of the current navigator object and speaks it")
	script_modified_review_nextCharacter.category=SCRCAT_TEXTREVIEW

	def script_forward_review_currentCharacter(self,gesture):
		#When speech review mode is enabled, the first character description is spoken on first script call.
		#When Braille review mode is set to "On" or "Auto", character descriptions are displayed on the first script call.
		CJK["direction"]=1
		info=api.getReviewPosition().copy()
		info.expand(textInfos.UNIT_CHARACTER)
		count = scriptHandler.getLastScriptRepeatCount()

		try:
			c = ord(info.text)
		except:
			c=0

		if count == 1 or (CJK["speechReview"] == "On" or CJK["brailleReview"] != "Off"):
			CJK["isReviewCharacter"] = True
			if count == 1 or CJK["speechReview"] == "On":
				speech.speakSpelling(info.text,useCharacterDescriptions=True)
			if CJK["brailleReview"] == "On" or CJK["brailleReview"] == "Auto":
				try:
					char = info.text.lower()
					charDesc = characterProcessing.getCharacterDescription(CJK["locale"], char)
					#speech.speakMessage("braille output: "+char+" "+" ".join(charDesc))
					BrailleHandler.message(handler, char+" "+" ".join(charDesc))
				except TypeError:
					pass
		elif count == 0:
			speech.speakTextInfo(info,unit=textInfos.UNIT_CHARACTER,reason=controlTypes.REASON_CARET)
		else:
			try:
				speech.speakMessage("%d," % c)
				speech.speakSpelling(hex(c))
			except:
				speech.speakTextInfo(info,unit=textInfos.UNIT_CHARACTER,reason=controlTypes.REASON_CARET)
		#Reset parameters to prepare for the next call.
		CJK["direction"] = 0
		CJK["isReviewCharacter"] = False
	script_forward_review_currentCharacter.__doc__=_("Reports the character of the current navigator object where the review "
"cursor is situated. Pressing twice reports a description or example of that "
"character. Pressing three times reports the numeric value of the character "
"in decimal and hexadecimal")
	script_forward_review_currentCharacter.category=SCRCAT_TEXTREVIEW

	def script_reverse_review_currentCharacter(self,gesture):
		CJK["direction"] = -1
		CJK["isReviewCharacter"] = True
		info=api.getReviewPosition().copy()
		info.expand(textInfos.UNIT_CHARACTER)
		speech.speakSpelling(info.text,useCharacterDescriptions=True)
		CJK["direction"] = 0
		CJK["isReviewCharacter"] = False
	script_reverse_review_currentCharacter.__doc__=_("Enumerates in reverse order through the list of character descriptions in the dictionary.")
	script_reverse_review_currentCharacter.category=SCRCAT_TEXTREVIEW

	def terminate(self):
		speech.getSpeechForSpelling = self.default_getSpeechForSpelling
		BrailleHandler._doCursorMove = self.default_doCursorMove
		InputComposition.reportNewText = self.default_reportNewText
		super(GlobalPlugin, self).terminate()

#: Dictionary for key bindings
	__gestures = {
		"kb:nvda+=": "ToggleBrailleReview",
		"kb:NVDA+0": "ToggleSpeechReview",
		"kb:numPad2": "forward_review_currentCharacter",
		"kb:Shift+numPad2": "reverse_review_currentCharacter",
		"kb:numpad1": "modified_reviewPreviousCharacter",
		"kb:numpad3": "modified_review_nextCharacter",
		"kb(laptop):NVDA+.": "forward_review_currentCharacter",
		"kb(laptop):NVDA+Shift+.": "reverse_review_currentCharacter",
		"kb(laptop):nvda+leftarrow": "modified_reviewPreviousCharacter",
		"kb(laptop):nvda+rightarrow": "modified_review_nextCharacter",
	}
