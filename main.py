import discord
from googletrans import Translator
import os
from dotenv import load_dotenv
from flask import Flask
import threading
import logging
import asyncio

# Configurer les logs pour mieux diagnostiquer les problèmes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration du bot Discord
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True  # Activer les intents pour les réactions
client = discord.Client(intents=intents)
translator = Translator()

# Configuration des salons et langues
channels = {
    "general": "en",
    "general-fr": "fr",
    "general-en": "en",
    "general-es": "es",
    "general-uk": "uk",
    "general-br": "pt",
    "general-cn": "zh-cn",
    "general-de": "de",
    "general-kr": "ko"
}

@client.event
async def on_ready():
    logger.info(f"Connecté en tant que {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Gestion des salons existants avec redirection
    if message.channel.name in channels:
        source_lang = channels[message.channel.name]
        for channel_name, target_lang in channels.items():
            if channel_name != message.channel.name:
                target_channel = discord.utils.get(message.guild.channels, name=channel_name)
                if target_channel:
                    try:
                        # Préparer le message à envoyer
                        formatted_message = f"**{message.author.name}**: "

                        # Gérer le texte s'il existe
                        if message.content:
                            translated = translator.translate(message.content, src=source_lang, dest=target_lang).text
                            formatted_message += translated
                        else:
                            formatted_message += "(Pas de texte)"

                        # Gérer les images (attachments)
                        if message.attachments:
                            attachment_urls = "\n".join([attachment.url for attachment in message.attachments])
                            formatted_message += f"\n{attachment_urls}"

                        # Envoyer le message au salon cible
                        await target_channel.send(formatted_message)

                    except Exception as e:
                        logger.error(f"Erreur lors du traitement du message vers {target_lang} : {e}")
                        await target_channel.send(f"Erreur : {e}")

    # Nouvelle fonctionnalité pour "event test"
    if message.channel.name == "event test" and not message.author.bot:
        try:
            await message.add_reaction('🇫🇷')  # Français
            await message.add_reaction('🇬🇧')  # Anglais
            await message.add_reaction('🇺🇦')  # Ukrainien
            await message.add_reaction('🇪🇸')  # Espagnol
            await message.add_reaction('🇩🇪')  # Allemand
            await message.add_reaction('🇰🇷')  # Coréen
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des réactions : {e}")

@client.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.channel.name != "event test":
        return

    lang_map = {
        '🇫🇷': 'fr',  # Français
        '🇬🇧': 'en',  # Anglais
        '🇺🇦': 'uk',  # Ukrainien
        '🇪🇸': 'es',  # Espagnol
        '🇩🇪': 'de',  # Allemand
        '🇰🇷': 'ko'   # Coréen
    }

    target_lang = lang_map.get(reaction.emoji.name)
    if target_lang:
        try:
            translated = translator.translate(reaction.message.content, dest=target_lang).text
            reply = await reaction.message.channel.send(
                f"{user.mention}, traduction en {target_lang}: {translated}"
            )
            # Supprime le message après 10 secondes
            await asyncio.sleep(10)
            await reply.delete()
        except Exception as e:
            logger.error(f"Erreur lors de la traduction ou de l'envoi : {e}")
            error_msg = await reaction.message.channel.send("Erreur lors de la traduction.")
            await asyncio.sleep(10)
            await error_msg.delete()

# Configuration du serveur Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/ping')
def ping():
    return "OK", 200  # Route keep-alive

# Fonction pour lancer le bot Discord avec reconnexion en cas d'erreur
def run_bot():
    while True:
        try:
            logger.info("Démarrage du bot Discord...")
            client.run(os.getenv("DISCORD_TOKEN"))
        except Exception as e:
            logger.error(f"Le bot s'est arrêté avec une erreur : {e}")
            logger.info("Tentative de reconnexion dans 5 secondes...")
            threading.Event().wait(5)  # Attendre 5 secondes avant de relancer

# Lancer Flask et le bot en parallèle
if __name__ == "__main__":
    # Démarrer le bot dans un thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    # Démarrer le serveur Flask dans le thread principal
    app.run(host='0.0.0.0', port=8080, debug=False)