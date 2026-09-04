@app.post("/api/interaction")
async def handle_interaction(data: UserInteraction, x_access_code: str = Header(None)):
    if x_access_code != ACCESS_CODE:
        logger.warning(f"Refus API Vocal - Code invalide: {x_access_code}")
        raise HTTPException(status_code=401, detail="Non autorisé")

    if not client_ai:
        logger.error("La clé OPENCODE_API_KEY est introuvable.")
        raise HTTPException(status_code=500, detail="OpenCode API Key non configurée")
    
    logger.info(f"Requête reçue de {data.user_id} depuis {data.location} : '{data.text_input}'")

    try:
        context_memories = ""
        if memory_client:
            try:
                # CORRECTION 1 : Utilisation du paramètre `filters` pour Mem0
                search_results = memory_client.search(
                    query=data.text_input, 
                    filters={'user_id': data.user_id}, 
                    limit=3
                )
                if search_results:
                    memories_list = [f"- {res['memory']}" for res in search_results]
                    context_memories = "\n".join(memories_list)
                    logger.info(f"Mem0 a trouvé {len(search_results)} souvenirs.")
            except Exception as mem_err:
                logger.error(f"Échec de la recherche Mem0 : {mem_err}")

        system_instruction = (
            "Tu es Onyx, un assistant embarqué de Citroën C4, intelligent, concis et factuel. "
            "Tu t'adresses à Pierre. Tes réponses doivent impérativement faire moins de 20 mots, "
            "être formulées de manière directe, et être adaptées à un contexte de conduite automobile.\n\n"
            f"Faits et souvenirs pertinents sur Pierre :\n{context_memories if context_memories else 'Aucun souvenir.'}"
        )

        logger.info("Envoi de la requête au modèle LLM...")
        completion = client_ai.chat.completions.create(
            model="GPT 5.4 Nano", 
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"[Lieu: {data.location}] {data.text_input}"}
            ],
            max_tokens=60,
            temperature=0.3
        )
        
        # CORRECTION 2 : Vérification dynamique du type de retour d'OpenCode
        if isinstance(completion, str):
            reply = completion.strip()
        elif hasattr(completion, 'choices') and completion.choices:
            reply = completion.choices[0].message.content.strip()
        else:
            reply = "Je n'ai pas de réponse."
            
        logger.info(f"Onyx répond : '{reply}'")

        if memory_client:
            try:
                memory_client.add(
                    messages=[
                        {"role": "user", "content": data.text_input},
                        {"role": "assistant", "content": reply}
                    ],
                    user_id=data.user_id
                )
                logger.info("Interaction sauvegardée dans Mem0.")
            except Exception as mem_err:
                logger.error(f"Échec sauvegarde Mem0 : {mem_err}")

        score = 5 if len(reply.split()) <= 25 else 3
        return {"status": "success", "reply": reply, "auto_score": score}
        
    except Exception as e:
        logger.error(f"Erreur critique backend : {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
