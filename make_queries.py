import json
from itertools import combinations
import pandas as pd
from IPAParser_2_0 import parse_consonant


### Helpers ###


def congruent(f1, f2):
    if f1 == f2:
        return True
    if f1 < f2:
        ordered = (f1, f2)
    else:
        ordered = (f2, f1)
    if ordered in {
        ('bilabial', 'labio-dental'),
        ('alveolar', 'dental')
    }:
        return True
    return False


### Segment processing ###


def feature_difference(p1, p2):
    parse1 = parse_consonant(p1)
    parse2 = parse_consonant(p2)
    parse_differences = {}
    for k in parse1:
        if k == 'glyph':
            continue
        if parse1[k] != parse2[k]:
            parse_differences[k] = {
                'p1': parse1[k],
                'p2': parse2[k]
            }
    return parse_differences


### Inventory processing ###


def get_inventory(data_frame, glottocode):
    return list(d.loc[d.Glottocode == glottocode].Phoneme)


def all_segments_parsable(inventory):
    for p in inventory:
        try:
            parse_consonant(p)
        except:
            return False
    return True


def get_manners(inventory, manners):
    return list(filter(
        lambda x: parse_consonant(x).get('manner', None) in manners,
        inventory
    ))


def get_voices(inventory, voices):
    return list(filter(
        lambda x: parse_consonant(x).get('voice', None) in voices,
        inventory
    ))


def voice_opp_in(inventory, manner):
    segs = get_manners(inventory, manner)
    opps = oppositions(segs, 'voice')
    if opps == {}:
        return False
    else:
        return opps


def oppositions(consonants, feature, others_same=True):
    """
    Returns pairs of consonants opposed by the value of
    a feature while values of all other features are kept
    fixed (default) or a free to vary.
    """
    results = {}
    for c1, c2 in combinations(consonants, 2):
        parse1 = parse_consonant(c1)
        parse2 = parse_consonant(c2)
        if feature not in parse1 or feature not in parse2:
            continue
        if parse1[feature] != parse2[feature]:
            if others_same:
                other_are_same = True
                for k in parse1:
                    if k == feature or k == 'glyph': 
                        continue
                    elif k in {
                        'additional articulations',
                        'pre-features'
                    }:
                        if sorted(parse1[k]) != sorted(parse2[k]):
                            other_are_same = False
                            break
                    else:
                        if not congruent(parse1[k], parse2[k]):
                            other_are_same = False
                            break
                if other_are_same:
                    results[(c1, c2)] = (parse1[feature], parse2[feature])
            else:
                results[(c1, c2)] = (parse1[feature], parse2[feature])
    return results


if __name__ == '__main__':
    from collections import defaultdict

    contributors = pd.read_csv('phoible-v2.0.1/cldf-datasets-phoible-f36deac/cldf/contributions.csv')
    name_and_source = {}
    for t in contributors.itertuples():
        name_and_source[t.ID] = (t.Name, t.Contributor_ID)

    d = pd.read_csv('phoible.csv')
    d = d.loc[ d.SegmentClass == 'consonant' ]

    # Select one inventory per glottocode.
    codes_to_ids = defaultdict(set)
    for t in d.itertuples():
        codes_to_ids[t.Glottocode].add(t.InventoryID)
    sample = [ max(v) for v in codes_to_ids.values() ]
    
    # Check that all consonants can be parsed.
    parsable_sample = set()
    for inv_id in sample:
        inventory = list(d.loc[ d.InventoryID == inv_id ].Phoneme)
        if all_segments_parsable(inventory):
            parsable_sample.add(inv_id)
    print(f'Sample size: {len(parsable_sample)}')

    d = d.loc[ d.apply(lambda row: row.InventoryID in parsable_sample, axis=1) ]
    for gltc in d.Glottocode.unique():
        inv_id = list(d.loc[ d.Glottocode == gltc ].InventoryID)[0]
        inv  = get_inventory(d, gltc)
        if not voice_opp_in(inv, ['stop']):
            continue
        opps = voice_opp_in(inv, ['affricate'])
        if opps:
            fricatives = get_manners(inv, ['fricative'])
            affricates = get_manners(inv, ['affricate'])
            voiced_affricates = list(filter(
                lambda x: parse_consonant(x)['voice'] == 'voiced',
                affricates))
            voiceless_affricates = list(filter(
                lambda x: parse_consonant(x)['voice'] == 'voiceless',
                affricates))
            # Check for voiced affricates that have paired
            # voiceless affricates and voiceless fricatives
            # but do not have paired voiced fricatives.
            result = []
            for affr_vcd in voiced_affricates:
                if oppositions([affr_vcd] + fricatives, 'manner'):
                    continue
                # Find the corresponding voiceless affricate.
                opps_tmp = oppositions([affr_vcd] + voiceless_affricates, 'voice')
                if opps_tmp:
                    for _, affr_vcl in opps_tmp:
                        # Does this voiceless affricate has a paired fricative?
                        if oppositions([affr_vcl] + fricatives, 'manner'):
                            result.append(affr_vcd)
            if result:
                remaninder = list(filter(lambda x: x not in result, voiced_affricates))
                print(gltc, name_and_source[inv_id][0], name_and_source[inv_id][1])
                print('Fricatives:', ', '.join(fricatives))
                print('Affricates:', ', '.join(affricates))
                print('Result:', ', '.join(result))
                print(f'Remainder: {", ".join(remaninder)}')
                print()
