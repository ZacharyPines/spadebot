# spadebot
An Opus Magnum python bot that uses om.py to solve levels where all output atoms are contained within input atoms. It cannot currently augment atoms, but the code is made to be readable so adding that functionality is possible.

Note: This is currently set up to run through hundreds of files, which means that  more specific debug information isn't printed per puzzle. To change that, set PRINT_DEBUG_MESSAGES to true and call the function once instead of using a for loop. You can call spadebot() directly instead of the handler to avoid emoji.
