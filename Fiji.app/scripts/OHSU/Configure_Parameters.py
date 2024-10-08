from fiji.util.gui import GenericDialogPlus
from ohsu.config.colocalisation_config import ColocalisationConfig
from ohsu.config.config import Config
from ohsu.config.core_config import CoreConfig
from ohsu.config.foci_config import FociConfig
from ohsu.config.nucleolus_config import NucleolusConfig
from ohsu.gui.config.channel_panel import ChannelPanel
from ohsu.gui.config.coloc_panel import ColocalisationPanel
from ohsu.gui.config.foci_panel import FociPanel
from ohsu.gui.config.measurements_panel import MeasurementsPanel
from ohsu.gui.config.nucleolus_panel import NucleolusPanel

def run():
    gd = GenericDialogPlus('Configure Parameters')

    channelPanel = ChannelPanel(gd)
    measurementsPanel = MeasurementsPanel(gd)
    colocPanel = ColocalisationPanel(gd)
    fociPanel = FociPanel(gd, channelPanel)
    nucleolusPanel = NucleolusPanel(gd, channelPanel)

    gd.addMessage('Core Configuration')
    gd.addComponent(channelPanel)
    gd.addComponent(measurementsPanel)
    gd.addComponent(colocPanel)
    gd.addComponent(fociPanel)
    gd.addComponent(nucleolusPanel)
   
    gd.showDialog()
    if (gd.wasCanceled()):
        return 0

    CoreConfig.setChannels(channelPanel.getChannels())
    CoreConfig.setMaskChannel(channelPanel.getMaskChannel())
    CoreConfig.setShouldRunCellMeasurements(measurementsPanel.getRunCellMeasurementsFlag())
    ColocalisationConfig.setChannel(colocPanel.getChannel())
    FociConfig.setChannels(fociPanel.getChannels())
    NucleolusConfig.setMaskChannel(nucleolusPanel.getMaskChannel())
    NucleolusConfig.setNucleolusChannel(nucleolusPanel.getNucleolusChannel())
    
    Config.save()

run()