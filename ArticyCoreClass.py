INDENT_SPACING = "    "

# --------------------------------------

class ArticyCore:
    """base class other objects inherit"""

    def __init__(self, theID, theName):
        self.ID = theID
        self.Name = theName

# --------------------------------------

class Character(ArticyCore):
    """ Collect character info from JSON"""

    def __init__(self, theID, theName, theColor, theAbbrev):
        ArticyCore.__init__(self, theID, theName)
        self.Color = theColor
        self.Abbrev = theAbbrev

    def __str__(self):
        return f"{self.ID}, {self.Name}, {self.Abbrev}"

# --------------------------------------

class FlowFrag(ArticyCore):
    """Collect flow fragments from JSON"""

    def __init__(self, theID, theName, theParent, theText, theOutputs):
        ArticyCore.__init__(self, theID, theName)
        self.ParentID = theParent
        self.OutputIDs = theOutputs
        self.Text = theText

    def __str__(self):
        return f"{self.ID}, {self.Name}, {self.ParentID}, {self.OutputIDs}"

# --------------------------------------

class RenpySearch:
    """ A common search routine for dialogs and renpy core"""

    def FindConnections(self, parentid, outputids: [], dialogs: [], conditions: [], instructions: [], codes: [], snippets: [], hubs: []):
        outputs = []
        for outputid in outputids:
            if parentid != outputid:  # ignore the last output in a dialog which always points to the parent
                found = None
                for dialog in dialogs:
                    if dialog.ID == outputid:
                        found = dialog
                if found == None:
                    for condition in conditions:
                        if condition.Frag.ID == outputid:
                            found = condition
                if found == None:
                    for instruction in instructions:
                        if instruction.Frag.ID == outputid:
                            found = instruction
                if found == None:
                    for code in codes:
                        if code.Frag.ID == outputid:
                            found = code
                if found == None:
                    for snippet in snippets:
                        if snippet.Frag.ID == outputid:
                            found = snippet
                if found == None:
                    for hub in hubs:
                        if hub.Frag.ID == outputid:
                            found = hub
                outputs.append(found)
                if found != None:
                    found.Inputs.append(self)

        return outputs

    def MakeConnections(self, scenes: [], dialogs: [], conditions: [], instructions: [], codes: [], snippets: [], hubs: []):
        for scene in scenes:
            if scene.Frag.ID == self.Frag.ParentID:
                self.Parent =  scene

        self.Outputs = self.FindConnections(self.Frag.ParentID, self.Frag.OutputIDs, dialogs, conditions, instructions, codes, snippets, hubs)

# --------------------------------------

class RenpyCore(RenpySearch):
    """A Renpy Core node from the flow fragments"""

    def __init__(self, frag: FlowFrag, template: str):
        self.Frag = frag
        tlen = len(template)
        names = self.Frag.Name.split()
        if names[0].lower()[:tlen] == template.lower():
            if len(names[0])>tlen:
                enum = names[0][tlen:]
            elif len(names)>1:
                names.pop(0)
                enum = names[0]
            else:
                enum = ''
            if enum.isnumeric():
                self.Num = int(enum)
                names.pop(0)
            else:
                self.Num = 0
            self.Desc = " ".join(names)
        else:
            self.Num = 0
            self.Desc = ''
        self.Parent: Scene = None
        self.Outputs = []
        self.Inputs = []
        self.Children = []
        self.First = None

    def __str__(self):
        return f"{self.Frag.ID} Renpy Core {self.Num}: {self.Desc}"

    def Title(self):
        return f"Renpy Core {self.Num}: {self.Desc}"

    def Next(self):
        if len(self.Outputs)>0:
            return self.Outputs[0]
        else:
            return None


    def LinkOutputs(self, candidates: []):
        self.Outputs.clear()
        for outputid in self.Frag.OutputIDs:
            for candidate in candidates:
                if outputid == candidate.Frag.ID:
                    self.Outputs.append(candidate)
                    candidate.Inputs.append(self)
    
    def FindPredecessor(self, candidates: []):
        if len(self.Inputs)>0:
            return self.Inputs[0]
        else:
            return None

    def MakeLinkages(self, renpyCores: []):
        # first identify all children of this core in the set renpyCores
        self.Children.clear()
        for renpy in renpyCores:
            if renpy.Frag.ParentID == self.Frag.ID:
                renpy.Parent = self
                self.Children.append(renpy)

        self.First = None
        if len(self.Children)>0:
            # next, if there are any children, link all the siblings by outputs
            for renpy in self.Children:
                renpy.LinkOutputs(self.Children)

            # finally, identify the first sibling
            self.First = self.Children[0]
            candidate = self.First.FindPredecessor(self.Children)
            while candidate!=None:
                self.First = candidate
                candidate = self.First.FindPredecessor(self.Children)

    def MakeRenpyExpressionFromDesc(self):
        expression = self.Desc

        i = expression.find('true')
        while i>= 0:
            expression = expression[:i] + 'T' + expression[i+1:]
            i = expression.find('true')

        i = expression.find('false')
        while i>= 0:
            expression = expression[:i] + 'F' + expression[i+1:]
            i = expression.find('true')

        prefix = expression.split('.')[0]
        l = len(prefix)+1
        return expression[l:]

# --------------------------------------

class RenpyContextCondition():
    # When traversing a scene's dialog, the context is used for logic control branches

    def __init__(self, theID, theStatement, theTruePath, theFalsePath):
        self.ID = theID
        self.Statement = theStatement
        self.IsTruePass = True
        self.TruePath = theTruePath
        self.FalsePath = theFalsePath

# --------------------------------------

class RenpyMenuItem():
    # information for each item in a menu

    def __init__(self, menutext, menupath, prefix):
        self.MenuText = menutext
        self.MenuPath = menupath
        menutag = menutext.lower()
        menutag = menutag.replace(' ', '_')
        menutag = menutag.replace('\'', '')
        self.MenuTag = prefix+"_"+menutag
        self.Followed = False


# --------------------------------------

class RenpyContextMenu():
    # When traversing a scene's dialog, the context is used for logic control branches

    def __init__(self, theID, menuitems: []):
        self.ID = theID
        self.MenuItems = menuitems.copy()

    def AddMenuInstructions(self, lines, indent):
        lines.append("")
        lines.append(indent+"menu:")
        indent += INDENT_SPACING
        lines.append(indent+f"\" \"")
        for menuitem in self.MenuItems:
            lines.append("")
            lines.append(indent+f"\"{menuitem.MenuText}\":")
            lines.append(indent+INDENT_SPACING+f"jump {menuitem.MenuTag}")

    def AddMenuPathStart(self, lines, indent):
        for menuitem in self.MenuItems:
            if not menuitem.Followed:
                lines.append("")
                lines.append(indent+f"label {menuitem.MenuTag}:")
                break

    def AddMenuPathEnd(self, lines, indent, nextpath):
        firstmenuend = None
        for menuitem in self.MenuItems:
            if menuitem.Followed:
                if (menuitem.MenuPath == nextpath) and (firstmenuend == None):
                    firstmenuend = menuitem
        lines.append("")
        lines.append(indent+f"jump {firstmenuend.MenuTag}_end")

    def AddMenuPathJoin(self, lines, indent, nextpath):
        firstmenuend = None
        for menuitem in self.MenuItems:
            if menuitem.Followed:
                if (menuitem.MenuPath == nextpath) and (firstmenuend == None):
                    firstmenuend = menuitem
        lines.append("")
        lines.append(indent+f"label {firstmenuend.MenuTag}_end:")

    def IsAnotherPath(self):
        for menuitem in self.MenuItems:
            if not menuitem.Followed:
                return True
        return False
        
    def MenuPathStart(self):
        for menuitem in self.MenuItems:
            if not menuitem.Followed:
                return menuitem.MenuPath

    def EndMenuPath(self, nextpath):
        for menuitem in self.MenuItems:
            if not menuitem.Followed:
                menuitem.MenuPath = nextpath
                menuitem.Followed = True
                break

    def CountMenuPaths(self, nextpath):
        count = 0
        for menuitem in self.MenuItems:
            if menuitem.Followed:
                if menuitem.MenuPath == nextpath:
                    count += 1
        return count


# --------------------------------------

class Episode(RenpyCore):
    """An episode defined from the flow fragments"""

    def __init__(self, frag: FlowFrag):
        RenpyCore.__init__(self, frag, 'Episode')

    def __str__(self):
        return f"{self.Frag.ID} Episode {self.Num}: {self.Desc}"

    def Title(self):
        return f"Episode {self.Num}: {self.Desc}"

    def Prefix(self):
        return f"ep{self.Num}"

# --------------------------------------

class Scene(RenpyCore):
    """A scene defined from the flow fragments"""

    def __init__(self, frag: FlowFrag):
        RenpyCore.__init__(self, frag, 'Scene')
        self.Images = []

    def __str__(self):
        return f"{self.Frag.ID} Scene {self.Num}: {self.Desc}"

    def Title(self):
        return f"Scene {self.Num}: {self.Desc}"

    def Prefix(self):
        if self.Parent == None:
            return "???????"
        else:
            t = "0"+str(self.Num)
            t = t[len(t)-2:]
            return f"{self.Parent.Prefix()}sc{t}"

    def PrepareDialog(self, dialogs: [], snippets: [], conditions: [], instructions: [], codes: []):
        # the assumption at this point is that the Dialog & Condition connections have been made: the parents and outputs are set

        # first idetify all children of this core in the set renpyCores
        self.Children.clear()
        for dialog in dialogs:
            if dialog.Parent == self:
                self.Children.append(dialog)
        for snippet in snippets:
            if snippet.Parent == self:
                self.Children.append(snippet)
        for condition in conditions:
            if condition.Frag.ParentID == self.Frag.ID:
                condition.Parent = self
                self.Children.append(condition)
        for instruction in instructions:
            if instruction.Frag.ParentID == self.Frag.ID:
                instruction.Parent = self
                self.Children.append(instruction)
        for code in codes:
            if code.Frag.ParentID == self.Frag.ID:
                code.Parent = self
                self.Children.append(code)

        self.First = None
        if len(self.Children)>0:
            # next, if there are any children, identify the first sibling
            self.First = self.Children[0]
            candidate = self.First.FindPredecessor(self.Children)
            while candidate != None:
                self.First = candidate
                candidate = self.First.FindPredecessor(self.Children)

    def CreateRenpyScene(self): # ******************* This is where most of the work is done ***********************
        renpy = []
        menuitems = []

        self.Images.clear()
        contextStack = []
        renpy.append(f"# ({self.Prefix()}) {self.Title()}")
        renpy.append("")
        indent = "    "
        renpy.append(f"label {self.Prefix()}:")
        walk = self.First
        while walk != None:
            # quick check in order to load all unique images
            if type(walk) == Dialog:
                imagename = walk.ImageName()
                if len(imagename) > 0:
                    try:
                        self.Images.index(imagename)
                    except:
                        self.Images.append(imagename)

            retestDialog = False
            if type(walk) == Condition:
                context = walk.CreateContext()
                contextStack.append(context)
                renpy.append("")
                renpy.append(indent+context.Statement)
                indent += INDENT_SPACING
                walk = context.TruePath
                retestDialog = True

            elif len(walk.Inputs) > 1:
                # this can either be a condition resolution or menu paths recombining
                if len(contextStack) > 0:
                    # currently, this is the resolution point of a condition
                    context = contextStack.pop()
                    if type(context)==RenpyContextCondition:
                        if context.IsTruePass:
                            renpy.append("")
                            renpy.append(indent[len(INDENT_SPACING):]+"else:")
                            context.IsTruePass = False
                            contextStack.append(context)
                            walk = context.FalsePath
                            retestDialog = True
                        else:
                            indent = indent[len(INDENT_SPACING):]
                    elif type(context)==RenpyContextMenu:
                        # Okay, the way Menu paths end is complex since not all paths can end at the same node

                        context.EndMenuPath(walk)

                        if context.CountMenuPaths(walk) == len(walk.Inputs):
                            indent = indent[len(INDENT_SPACING):]
                            context.AddMenuPathJoin(renpy, indent, walk)
                            if context.IsAnotherPath():
                                contextStack.append(context)
                            # otherwise we are done with this menu, just continue
                        else:
                            context.AddMenuPathEnd(renpy, indent, walk)
                            indent = indent[len(INDENT_SPACING):]
                            if context.IsAnotherPath():
                                contextStack.append(context)
                                context.AddMenuPathStart(renpy, indent)
                                indent += INDENT_SPACING
                                walk = context.MenuPathStart()
                                retestDialog = True
                            else:
                                raise Exception("Missing menu path in CreateRenpyScene")

                    else:
                        raise Exception("Unknown context in CreateRenpyScene")

                else: 
                    raise Exception("Context Stack empty in CreateRenpyScene")

            if not retestDialog:
                # if a condition statement was found, the next node is selected and must be re-tested before the renpy statements are created
                imagename = walk.ImageName()
                if len(imagename) > 0:
                    renpy.append("")
                    renpy.append(indent+f"scene {imagename}{walk.ImageModifier()}")
                lines = walk.GenerateRenpy()
                if len(lines) > 0:
                    for line in lines:
                        renpy.append(indent+line)
                else:
                    renpy.append(indent+"pause")

                # Here's where we test for a menu
                if len(walk.Outputs) > 1:
                    menuitems.clear()
                    IsMenu = True
                    for output in walk.Outputs:
                        if type(output) == Dialog:
                            if len(output.MenuText) > 0:
                                menuitems.append(RenpyMenuItem(output.MenuText, output, self.Prefix()))
                            else:
                                raise Exception("Missing MenuText for menu")
                        else:
                            # Turns out, this is some sort of state machine diagram
                            # This is poorly defined - needs more distinct encoding
                            IsMenu = False
                    if IsMenu:
                        context = walk.CreateMenuContext(menuitems)
                        contextStack.append(context)

                        context.AddMenuInstructions(renpy, indent)
                        context.AddMenuPathStart(renpy, indent)
                        indent += INDENT_SPACING
                        walk = context.MenuPathStart()
                    else:
                        for output in walk.Outputs:
                            renpy.append("")
                            renpy.append(indent+f"call {output.Prefix()} # {output.Desc}")
                        # Again, this is not well thought out. Need a way to define a state machine link as opposed to a single link to be followed
                        walk = None

                else:
                    walk = walk.Next()

        renpy.append("")
        renpy.append(f"    return")
        return renpy

# --------------------------------------

class Game(RenpyCore):
    """A highest level node defined from the flow fragments"""

    def __init__(self, frag: FlowFrag):
        RenpyCore.__init__(self, frag, 'Game')

    def __str__(self):
        return f"{self.Frag.ID} {self.Desc}"

    def Title(self):
        return f"Game: {self.Desc}"

# --------------------------------------

class Dialog(RenpySearch):
    """A dialog line defined from the flow fragments"""

    def __init__(self, theID, theParent, theMenuText,  theStageDirections, theSpeaker, theText, theOutputs):
        self.ID = theID
        self.ParentID = theParent
        self.MenuText = theMenuText
        self.StageDirections = theStageDirections
        self.SpeakerID = theSpeaker
        self.Text = theText
        self.OutputIDs = theOutputs

        self.Speaker: Character = None
        self.Parent: Scene = None
        self.Outputs = []
        self.Inputs = []

    def __str__(self):
        if self.Parent == None:
            scene = '?'
        else:
            scene = self.Parent.Num

        if self.Speaker == None:
            speaker = 'UNDEF'
        else:
            speaker = self.Speaker.Abbrev

        outputs = ''
        for output in self.Outputs:
            if output == None:
                outputs += 'NULL'
            elif type(output) == Dialog:
                if output.Speaker == None:
                    outputs += 'UNK'
                else:
                    outputs += output.Speaker.Abbrev
            elif type(output) == Condition:
                outputs += 'COND'
            else:
                outputs += 'BAD'

        return f"Scene {scene}: {speaker} \"{self.Text}\" ({outputs})"

    def MakeConnections(self, scenes: [], characters: [], dialogs: [], conditions: [], instructions: [], codes: [], snippets: [], hubs: []):
        for scene in scenes:
            if scene.Frag.ID == self.ParentID:
                self.Parent =  scene

        for snippet in snippets:
            if snippet.Frag.ID == self.ParentID:
                self.Parent =  snippet

        for character in characters:
            if character.ID == self.SpeakerID:
                self.Speaker =  character

        self.Outputs = self.FindConnections(self.ParentID, self.OutputIDs, dialogs, conditions, instructions, codes, snippets, hubs)

    def FindPredecessor(self, candidates: []):
        if len(self.Inputs)>0:
            return self.Inputs[0]
        else:
            return None

    def Next(self):
        if len(self.Outputs)>0:
            return self.Outputs[0]
        else:
            return None

    def GenerateRenpy(self):
        commands = []
        lines = self.Text.split("\n")
        if self.Speaker == None:
            speaker = 'UNDEF'
        else:
            speaker = self.Speaker.Abbrev

        if speaker == 'command':
            for line in lines:
                if len(line.strip())>0:
                    commands.append(line.strip())
        else:
            for line in lines:
                if len(line.strip())>0:
                    commands.append(f"{speaker} \"{line.strip()}\"")

        return commands

    def ImageName(self):
        inameparts = self.StageDirections.split('|')
        iname = inameparts[0].strip()
        if len(iname) > 0:
            return f"{self.Parent.Prefix()} {iname}"
        else:
            return ''

    def ImageModifier(self):
        inameparts = self.StageDirections.split('|')
        imodifier = ''
        if len(inameparts)>1:
            imodifier = inameparts[1].strip()
        else:
            imodifier = "dissolve"
        if len(imodifier) > 0:
            return f" with {imodifier}"
        else:
            return ''

    def CreateMenuContext(self, menuitems: []):
        context = RenpyContextMenu(self.ID, menuitems)
        return context

# --------------------------------------

class Condition(RenpyCore):
    """A condition node used in dialogs"""
    UniqueID = 0

    def __init__(self, frag: FlowFrag, expression):
        ArticyCore.__init__(self, frag.ID, frag.Name)
        self.Frag = frag
        self.Num = 0
        self.Desc = expression
        self.Parent: Scene = None
        self.Outputs = []
        self.Inputs = []
        self.Children = []
        self.First = None

    def __str__(self):
        return f"{self.ID} Condition: {self.Desc}"

    def GenerateRenpy(self):
        lines = []
        lines.append('COND')
        return lines

    def ImageName(self):
        return ''

    def CreateContext(self):
        expression = self.MakeRenpyExpressionFromDesc()
        if len(self.Outputs)>0:
            truepath = self.Outputs[0]
            if len(self.Outputs)>1:
                falsepath = self.Outputs[1]
            else:
                falsepath = None
        else:
            truepath = None
            falsepath = None
        context = RenpyContextCondition(self.ID, f"if {expression}:", truepath, falsepath)
        return context

# --------------------------------------

class Instruction(RenpyCore):
    """An instruction node used in dialogs"""
    UniqueID = 0

    def __init__(self, frag: FlowFrag, expression):
        ArticyCore.__init__(self, frag.ID, frag.Name)
        self.Frag = frag
        self.Num = 0
        self.Desc = expression
        self.Parent: Scene = None
        self.Outputs = []
        self.Inputs = []
        self.Children = []
        self.First = None

    def __str__(self):
        return f"{self.ID} Condition: {self.Desc}"

    def GenerateRenpy(self):
        lines = []
        lines.append("")
        lines.append(f"$ {self.MakeRenpyExpressionFromDesc()}")
        return lines

    def ImageName(self):
        return ''

# --------------------------------------

class Hub(RenpyCore):
    """A hub node used in dialogs"""
    UniqueID = 0

    def __str__(self):
        return f"{self.Frag.ID} Hub"

    def GenerateRenpy(self):
        lines = []
        lines.append("")
        return lines

    def ImageName(self):
        return ''

# --------------------------------------

class Code(RenpyCore):
    """A code block defined from the flow fragments"""

    def __init__(self, frag: FlowFrag):
        RenpyCore.__init__(self, frag, 'Code')
        self.Text = frag.Text

    def __str__(self):
        return f"{self.Frag.ID} Code: {self.Desc}"

    def GenerateRenpy(self):
        commands = []
        lines = self.Text.split("\n")

        commands.append("")
        for line in lines:
            if len(line.strip())>0:
                commands.append(f"# {line.strip()}")
        return commands

    def ImageName(self):
        return ''

# --------------------------------------

class Snippet(Scene):
    """A snippet is defined from the flow fragments and is a subset of a fulle dialogue """

    def __init__(self, frag: FlowFrag):
        RenpyCore.__init__(self, frag, 'Snippet')
        self.Images = []

    def __str__(self):
        return f"{self.Frag.ID} Snippet {self.Num}: {self.Desc}"

    def Title(self):
        return f"Snippet {self.Num}: {self.Desc}"

    def Prefix(self):
        if self.Parent == None:
            return "???????"
        else:
            t = "0"+str(self.Num)
            t = t[len(t)-2:]
            return f"{self.Parent.Prefix()}sn{t}"

    def GenerateRenpy(self):
        commands = []
        commands.append("")
        commands.append(f"call {self.Prefix()} # {self.Desc}")
        return commands

    def ImageName(self):
        return ''







