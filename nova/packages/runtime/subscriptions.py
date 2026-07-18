from typing import Callable
from nova.packages.compiler import KnowledgeCommit

SubscriptionCallback = Callable[[KnowledgeCommit], None]
