import discord
from googletrans import Translator
import os
from dotenv import load_dotenv
from flask import Flask
import threading
import logging
from datetime import datetime, timedelta

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Configuration du bot Discord
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
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

# Mapping des drapeaux aux langues pour event-test (limité à 3 pour réduire la charge)
lang_map = {
    '🇫🇷': 'fr',  # Français
    '🇬🇧': 'en',  # Anglais
    '🇪🇸': 'es'   # Espagnol
}

@client.event
async def on_ready():
    logger.info(f"Connecté en tant que {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:  # Ignorer les messages du bot lui-même
        return

    logger.info(f"Message reçu dans {message.channel.name} par {message.author.name}: {message.content}")

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
                            content_added = False
                            if message.stickers:
                                sticker_info = "\n".join([f"Sticker: {sticker.name}" for sticker in message.stickers])
                                formatted_message += f"\n{sticker_info}"
                                content_added = True
                            if message.attachments:
                                attachment_urls = "\n".join([attachment.url for attachment in message.attachments])
                                formatted_message += f"\n{attachment_urls}"
                                content_added = True
                            if not content_added:
                                formatted_message += "(Message vide)"

                        logger.info(f"Envoi unique vers {channel_name}: {formatted_message}")
                        await target_channel.send(formatted_message)

                    except Exception as e:
                        logger.error(f"Erreur lors du traitement du message vers {target_lang} : {e}")
                        await target_channel.send(f"Erreur : {e}")

    # Gestion de "event-test" avec limitation des réactions
    elif message.channel.name == "event-test" and not message.author.bot:
        try:
            # Ajouter les réactions avec gestion des rate limits
            for flag in lang_map.keys():
                try:
                    await message.add_reaction(flag)
                    await client.wait_for('rate_limited', timeout=1.0)  # Attendre si rate limit
                except discord.HTTPException as e:
                    logger.error(f"Rate limit lors de l'ajout de {flag} : {e}")
                    await message.channel.send(f"Rate limit atteint, réaction {flag} non ajoutée.")
                    break
                await discord.utils.sleep_until(datetime.now() + timedelta(seconds=1))  # Délai de 1 seconde
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des réactions : {e}")

@client.event
async def on_reaction_add(reaction, user):
    if user == client.user or reaction.message.channel.name != "event-test":
        return

    emoji = str(reaction.emoji)
    target_lang = lang_map.get(emoji)
    
    if target_lang:
        try:
            message = await reaction.message.channel.fetch_message(reaction.message.id)
            if message.content:
                logger.info(f"Réaction détectée : {emoji} par {user.name}, traduction en {target_lang}")
                translated = translator.translate(message.content, dest=target_lang).text
                reply = await reaction.message.channel.send(f"{user.mention} {translated}")
                await discord.utils.sleep_until(datetime.now() + timedelta(seconds=10))  # Attente avant suppression
                await reply.delete()
            else:
                logger.info(f"Message sans contenu texte : {message.id}")
        except Exception as e:
            logger.error(f"Erreur lors de la traduction : {e}")
            error_msg = await reaction.message.channel.send(f"{user.mention}, erreur lors de la traduction.")
            await discord.utils.sleep_until(datetime.now() + timedelta(seconds=10))
            await error_msg.delete()

# Configuration du serveur Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/ping')
def ping():
    return "OK", 200

# Fonction pour lancer le bot Discord avec reconnexion
def run_bot():
    while True:
        try:
            logger.info("Démarrage du bot Discord...")
            client.run(os.getenv("DISCORD_TOKEN"))
        except Exception as e:
            logger.error(f"Erreur fatale dans run_bot : {e}", exc_info=True)
            logger.info("Tentative de reconnexion dans 5 secondes...")
            threading.Event().wait(5)

# Lancer Flask et le bot en parallèle
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    app.run(host='0.0.0.0', port=8080, debug=False)