from fiji.util.gui import GenericDialogPlus
from ij import IJ
from java.awt.event import ActionListener, ItemListener
from java.awt import Button, Checkbox, GridLayout, Label, Panel, TextField
from ohsu.config.core_config import CoreConfig
from ohsu.config.colocalisation_config import ColocalisationConfig
from ohsu.gui.ohsu_panel import OHSUPanel

def run():
    gd = GenericDialogPlus('Instructions')

    state = State()
    channelPanel = ChannelPanel(gd)
    colocPanel = ColocalisationPanel(gd)

    channelPanel.setLayout(GridLayout(0,1))

    gd.addMessage('Core Configuration')

    for channel, channelName in CoreConfig.getChannels().items():
        channelPanel.addChannel(channel, channelName)

    gd.addComponent(channelPanel)
    gd.addButton('Add Channel', AddChannelHandler(channelPanel))

    gd.addStringField('Mask Channel', CoreConfig.getMaskChannel(), 35)
    
    gd.addComponent(colocPanel)

    gd.addButton('Save', state)
   
    gd.showDialog()
    if (gd.wasCanceled()):
        return 0

'''
CHANNELS
'''
class ChannelPanel(OHSUPanel):

    def getChannels(self):
        components = self.getComponents()
        channels = {}
        for component in components:
            idx = component.getComponent(0).getText()
            name = component.getComponent(1).getText()
            channels[idx] =  name
        return channels

    def addChannel(self, channelNumber, name):
        panelRow = Panel()
        channelNumber = str(channelNumber)
        removeButton = Button('Remove')
        removeButton.addActionListener(RemoveChannelHandler(self, channelNumber))
        panelRow.add(Label(channelNumber))
        panelRow.add(TextField(name, 35))
        panelRow.add(removeButton)
        self.add(panelRow)
        self.repaintDialog()

    def removeChannel(self, channelNumber):
        self.remove(self.getComponentForChannel(channelNumber))
        self.regenerateChannelComponents()
        self.repaintDialog()

    def regenerateChannelComponents(self):
        components = self.getComponents()
        for idx, component in enumerate(components):
            newChannelNum = str(idx + 1)
            channelNumLabel = component.getComponent(0)
            channelButton = component.getComponent(2)

            channelNumLabel.setText(newChannelNum)
            [channelButton.removeActionListener(listener) for listener in channelButton.getActionListeners()]
            channelButton.addActionListener(RemoveChannelHandler(self, newChannelNum))


    def getComponentForChannel(self, channelNumber):
        components = self.getComponents()
        IJ.log('remove ' + channelNumber)
        return components[int(channelNumber) - 1]

class AddChannelHandler(ActionListener):

    def __init__(self, channelPanel):
        self.channelPanel = channelPanel
        super(ActionListener, self).__init__()

    def actionPerformed(self, event):
        existingChannels = self.channelPanel.getChannels()
        self.channelPanel.addChannel(len(existingChannels) + 1, '')

class RemoveChannelHandler(ActionListener):
    
    def __init__(self, channelPanel, channelNumber):
        self.channelPanel = channelPanel
        self.channelNumber = channelNumber
        super(ActionListener, self).__init__()

    def actionPerformed(self, event):
        self.channelPanel.removeChannel(self.channelNumber)


'''
COLOCALISATION
'''
class ColocalisationPanel(OHSUPanel):

    def __init__(self, gd):
        OHSUPanel.__init__(self, gd)
        isEnabled = ColocalisationConfig.getChannel() is not None
        self.checkbox = Checkbox('Enable colocalisation', isEnabled)
        self.checkbox.addItemListener(self.ToggleHandler(self))
        self.textPanel = Panel()
        self.textPanel.add(Label('Channel'))
        self.textPanel.add(TextField(35))
        self.buildInitial()

    def buildInitial(self):
        self.setLayout(GridLayout(0, 1))
        self.add(self.checkbox)
        self.handleToggleChange()

    def handleToggleChange(self):
        if self.checkbox.getState():
            self.add(self.textPanel)
        else:
            self.remove(self.textPanel)
        self.repaintDialog()

    class ToggleHandler(ItemListener):
        
        def __init__(self, colocPanel):
            super(ItemListener, self).__init__()
            self.colocPanel = colocPanel

        def itemStateChanged(self, event):
            self.colocPanel.handleToggleChange()



class State(ActionListener):
    def actionPerformed(self, event):
        IJ.log('done')

run()