import argparse
import json

from ArticyCoreClass import ArticyCore
from ArticyCoreClass import Character
from ArticyCoreClass import FlowFrag
from ArticyCoreClass import Episode
from ArticyCoreClass import Scene
from ArticyCoreClass import Dialog
from ArticyCoreClass import Condition
from ArticyCoreClass import Instruction
from ArticyCoreClass import Snippet
from ArticyCoreClass import Code
from ArticyCoreClass import Game
from ArticyCoreClass import Hub

parser = argparse.ArgumentParser(description='Convert the JSON file from Articy to a Renpy file')
parser.add_argument('-i', required=True, help='JSON file created by Articy (required)')
parser.add_argument('-o', required=False, help='Renpy file created from the JSON file')

args = parser.parse_args()

#print(args)
#print(args.i)

#-------------------------------------------------------------------------------
f = open(args.i)
data = json.load(f)
f.close()

TheGame: Game = None
Characters = []
FlowFrags = []
Episodes = []
Scenes = []
Dialogs = []
Conditions = []
Snippets = []
Codes = []
Instructions = []
Hubs = []

#-------------------------------------------------------------------------------
# parse the JSON file, building up internal data structures

for package in data['Packages']:
    for model in package['Models']:
        if model['Type']=='DialogueFragment':
            properties = model['Properties']
            outputpins = properties['OutputPins']
            outputs = []
            for outputpin in outputpins:
                connections = outputpin['Connections']
                for connection in connections:
                    outputs.append(connection['Target'])
            dialog = Dialog(properties['Id'], properties['Parent'], properties['MenuText'], properties['StageDirections'], properties['Speaker'], properties['Text'], outputs)
            Dialogs.append(dialog)

        elif model['Type']=='Instruction':
            properties = model['Properties']
            outputpins = properties['OutputPins']
            outputs = []
            for outputpin in outputpins:
                connections = outputpin['Connections']
                for connection in connections:
                    outputs.append(connection['Target'])
            frag = FlowFrag(properties['Id'], properties['DisplayName'], properties['Parent'], properties['Text'], outputs)
            instruction = Instruction(frag, properties['Expression'])
            Instructions.append(instruction)

        elif model['Type']=='Condition':
            properties = model['Properties']
            outputpins = properties['OutputPins']
            outputs = []
            for outputpin in outputpins:
                connections = outputpin['Connections']
                for connection in connections:
                    outputs.append(connection['Target'])
            frag = FlowFrag(properties['Id'], properties['DisplayName'], properties['Parent'], properties['Text'], outputs)
            condition = Condition(frag, properties['Expression'])
            Conditions.append(condition)

        elif model['Type']=='Hub':
            properties = model['Properties']
            outputpins = properties['OutputPins']
            outputs = []
            for outputpin in outputpins:
                connections = outputpin['Connections']
                for connection in connections:
                    outputs.append(connection['Target'])
            frag = FlowFrag(properties['Id'], properties['DisplayName'], properties['Parent'], properties['Text'], outputs)
            hub = Hub(frag, "hub")
            Hubs.append(hub)

        elif model['Type']=='DefaultMainCharacterTemplate_02':
            properties = model['Properties']
            color = properties['Color']
            template = model['Template']
            basic = template['DefaultBasicCharacterFeature_02']
            colorR = round(255*color['r'])
            colorG = round(255*color['g'])
            colorB = round(255*color['b'])
            char = Character(properties['Id'], properties['DisplayName'], (colorR, colorG, colorB), basic['AbreviatedName'])
            Characters.append(char)

        elif (model['Type']=='FlowFragment') or (model['Type']=='Dialogue'):
            properties = model['Properties']
            outputpins = properties['OutputPins']
            outputs = []
            for outputpin in outputpins:
                if 'Connections' in outputpin:
                    connections = outputpin['Connections']
                    for connection in connections:
                        outputs.append(connection['Target'])
            frag = FlowFrag(properties['Id'], properties['DisplayName'], properties['Parent'], properties['Text'], outputs)
            FlowFrags.append(frag)
        
            names = frag.Name.split()
            if names[0].lower()[:7] == 'episode':
                episode = Episode(frag)
                Episodes.append(episode)
            elif names[0].lower()[:5] == 'scene':
                scene = Scene(frag)
                Scenes.append(scene)
            elif names[0].lower()[:7] == 'snippet':
                scene = Snippet(frag)
                Snippets.append(scene)
            elif names[0].lower()[:4] == 'code':
                scene = Code(frag)
                Codes.append(scene)
            elif names[0].lower()[:4] == 'game':
                TheGame = Game(frag)

        else:
            print('Unhandled ???')
            print(model['Type'])
            print()

#-------------------------------------------------------------------------------
# For debug purposes, print out the data structures created from parsing the JSON file

print('Characters:')
Characters.sort(key=lambda character: character.Name)
for char in Characters:
    print(char)

print()

print('FlowFrags:')
for frag in FlowFrags:
    print(frag)

print()

print('Game:')
print(TheGame)

print()

print('Episodes:')
Episodes.sort(key=lambda episode: episode.Num)
for episode in Episodes:
    print(episode)

print()

print('Scenes:')
Scenes.sort(key=lambda scene: scene.Num)
for scene in Scenes:
    print(scene)

print()

print('Snippets:')
Snippets.sort(key=lambda snippet: snippet.Num)
for snippet in Snippets:
    print(snippet)

print()

print('Dialogs:')
for dialog in Dialogs:
#    if dialog.StageDirections == 'aurora smirks':
    if dialog.StageDirections == 'art sad':
        debug = 1
    dialog.MakeConnections(Scenes, Characters, Dialogs, Conditions, Instructions, Codes, Snippets, Hubs)
for dialog in Dialogs:
    print(dialog)

print()

def Connections(name, clist: []):
    print(name+":")
    for citem in clist:
        citem.MakeConnections(Scenes, Dialogs, Conditions, Instructions, Codes, Snippets, Hubs)
        print(citem)
    print()

Connections('Conditions', Conditions)
Connections('Instructions', Instructions)
Connections('Code Blocks', Codes)
Connections('Snippets', Snippets)
Connections('Hubs', Hubs)

#-------------------------------------------------------------------------------
# Now translate the structures into a Ren'Py representation

TheGame.MakeLinkages(Episodes)
print(TheGame.Title())
episode = TheGame.First
while episode != None:
    print('  ', episode.Title())
    episode.MakeLinkages(Scenes)
    scene = episode.First
    while scene != None:
        print('    ', f"({scene.Prefix()})", scene.Title())
        scene = scene.Next()

    print()
    episode = episode.Next()

print()

for scene in Scenes:
    scene.PrepareDialog(Dialogs, Snippets, Conditions, Instructions, Codes)
    lines = scene.CreateRenpyScene()
    if len(lines) > 0:
        print(f"({scene.Prefix()}) {scene.Title()}")
        print()
        for line in lines:
            print(line)
        print()

for snippet in Snippets:
    snippet.PrepareDialog(Dialogs, Snippets, Conditions, Instructions, Codes)
    lines = snippet.CreateRenpyScene()
    if len(lines) > 0:
        print(f"({snippet.Prefix()}) {snippet.Title()}")
        print()
        for line in lines:
            print(line)
        print()

for scene in Scenes:
    if len(scene.Images) > 0:
        print(f"({scene.Prefix()}) {scene.Title()}")
        for imagename in scene.Images:
            print(imagename)
    print()

for snippet in Snippets:
    if len(snippet.Images) > 0:
        print(f"({snippet.Prefix()}) {snippet.Title()}")
        for imagename in snippet.Images:
            print(imagename)
    print()

print()

#-------------------------------------------------------------------------------
# write Rnpy code out to the specified file

if args.o != None:
    f = open(args.o, "w")

    # The code files

    for scene in Scenes:
        lines = scene.CreateRenpyScene()
        if len(lines) > 0:
            for line in lines:
                f.write(f"{line}\n")
            f.write("\n")

    for snippet in Snippets:
        lines = snippet.CreateRenpyScene()
        if len(lines) > 0:
            for line in lines:
                f.write(f"{line}\n")
            f.write("\n")

    # List out the images needed

    for scene in Scenes:
        if len(scene.Images) > 0:
            for imagename in scene.Images:
                f.write(f"{imagename}\n")
        f.write("\n")

    for snippet in Snippets:
        if len(snippet.Images) > 0:
            for imagename in snippet.Images:
                f.write(f"{imagename}\n")
        f.write("\n")

    f.close()




