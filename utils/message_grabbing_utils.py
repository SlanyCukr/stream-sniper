def find_tagged_user_id(message, known_chatters):
    """
    Finds tagged user id in known chatters. Not searching in `chatter` database for performance reasons.
    Only searching for one user, I don't care if there are more tagged.
    :param message: Message from chat
    :param known_chatters: Dictionary of known chatters
    :return: ID of the tagged user
    """
    if '@' not in message:
        return None

    message = message.lower()
    at_sign_index = message.find('@')
    end_of_nick_index = message.find(' ', at_sign_index)

    if end_of_nick_index == -1:
        nick = message[at_sign_index + 1:]
    else:
        nick = message[at_sign_index + 1:end_of_nick_index]

    if nick in known_chatters:
        return known_chatters[nick]
