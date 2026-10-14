"""
Deep Knowledge Tracing (DKT) GRU Model Architecture for StudyMind.
Implements sequential knowledge tracing using recurrent gated units with masked loss computation.
Reference: Piech et al., Deep Knowledge Tracing (NIPS 2015).
"""

import torch
import torch.nn as nn
from typing import Dict, Any, Tuple


class DKTGRUModel(nn.Module):
    """
    GRU-based Deep Knowledge Tracing Neural Network.
    
    Inputs:
        interaction_seq: LongTensor of shape (batch_size, seq_len)
          where interaction token = 1 + skill_id + is_correct * num_skills (0 is padding).
    Outputs:
        skill_predictions: Tensor of shape (batch_size, seq_len, num_skills)
          logits or probabilities of correctness for all skills at next step.
    """

    def __init__(
        self,
        num_skills: int = 15,
        embed_dim: int = 64,
        hidden_dim: int = 64,
        num_layers: int = 1,
        dropout: float = 0.2
    ):
        super(DKTGRUModel, self).__init__()
        self.num_skills = num_skills
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # Padding index is 0, interaction tokens range from 1 to 2 * num_skills
        self.embedding = nn.Embedding(
            num_embeddings=2 * num_skills + 1,
            embedding_dim=embed_dim,
            padding_idx=0
        )

        self.gru = nn.GRU(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )

        self.dropout = nn.Dropout(dropout)
        self.out_proj = nn.Linear(hidden_dim, num_skills)

    def forward(self, interaction_seq: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Args:
            interaction_seq: (batch_size, seq_len)
        Returns:
            logits: (batch_size, seq_len, num_skills)
        """
        # Embed interactions
        embedded = self.embedding(interaction_seq)  # (B, T, embed_dim)
        embedded = self.dropout(embedded)

        # Pass through GRU
        gru_out, _ = self.gru(embedded)  # (B, T, hidden_dim)
        gru_out = self.dropout(gru_out)

        # Project to all skills
        logits = self.out_proj(gru_out)  # (B, T, num_skills)
        return logits

    @torch.no_grad()
    def predict_next_skills(self, interaction_tokens: list) -> torch.Tensor:
        """
        Given a student's chronological interaction tokens, predicts current mastery
        probability for every skill.
        Returns tensor of shape (num_skills,) with probabilities in [0, 1].
        """
        self.eval()
        if not interaction_tokens:
            # Cold start: return neutral 0.5 prior
            return torch.full((self.num_skills,), 0.5)

        inp = torch.tensor([interaction_tokens], dtype=torch.long)
        logits = self.forward(inp)  # (1, T, num_skills)
        last_step_logits = logits[0, -1, :]  # (num_skills,)
        probs = torch.sigmoid(last_step_logits)
        return probs
